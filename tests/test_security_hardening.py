"""Isolated real SQLite/crypto contracts. Framework imports remain test doubles."""
import base64
from collections import OrderedDict
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid
import warnings
from urllib.parse import urlsplit
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from test_security_contracts import definitions, HTTPError, ROOT


def complete(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as stopped:
        return stopped.value
    raise AssertionError("Unexpected asynchronous IO")


class DB:
    def __init__(self, filename=":memory:"):
        self.connection = sqlite3.connect(filename)
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql, params=None):
        cursor = self.connection.execute(sql, params or {})
        rows = cursor.fetchall() if cursor.description else []
        count = cursor.rowcount
        cursor.close()
        return SimpleNamespace(rowcount=count, mappings=lambda: SimpleNamespace(first=lambda: dict(rows[0]) if rows else None))

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()


class OAuthContracts(unittest.TestCase):
    def setUp(self):
        self.db = DB()
        self.db.execute("CREATE TABLE oauth_attempts (state_hash TEXT PRIMARY KEY, browser_hash TEXT, user_id TEXT, client_id TEXT, platform TEXT, expires_at TIMESTAMP, consumed_at TIMESTAMP)")
        self.addCleanup(self.db.connection.close)
        self.target = definitions("app/utils/oauth_state.py",
            ["_digest", "cookie_name", "cookie_path", "issue_oauth_attempt", "consume_oauth_attempt", "finish_oauth"],
            hashlib=hashlib, secrets=secrets, re=re, datetime=datetime, timedelta=timedelta, text=lambda sql: sql, TTL_SECONDS=600)

    def begin(self, platform="google_ads", production=False):
        response = SimpleNamespace(set_cookie=Mock(), headers={})
        state = self.target.issue_oauth_attempt(self.db, response, "owner-1", "client-1", platform,
                                               SimpleNamespace(app_env="production" if production else "test"))
        browser = response.set_cookie.call_args.args[1]
        request = SimpleNamespace(cookies={self.target.cookie_name(platform, production): browser})
        return state, browser, request, response

    def test_hashes_only_cookie_flags_and_ttl(self):
        state, browser, _, response = self.begin(production=True)
        row = self.db.connection.execute("SELECT * FROM oauth_attempts").fetchone()
        self.assertNotEqual(row["state_hash"], state)
        self.assertNotEqual(row["browser_hash"], browser)
        self.assertEqual(len(row["state_hash"]), 64)
        options = response.set_cookie.call_args.kwargs
        self.assertTrue(options["secure"])
        self.assertTrue(options["httponly"])
        self.assertEqual(options["samesite"], "lax")
        self.assertEqual(options["max_age"], 600)
        self.assertEqual(options["path"], "/")
        self.assertTrue(response.set_cookie.call_args.args[0].startswith("__Host-"))

    def test_owner_client_returned_and_replay_blocked_for_both_providers(self):
        for platform in ("google_ads", "meta_ads"):
            state, _, request, _ = self.begin(platform)
            self.assertEqual(self.target.consume_oauth_attempt(self.db, request, state, platform),
                             {"user_id": "owner-1", "client_id": "client-1"})
            with self.assertRaises(HTTPError):
                self.target.consume_oauth_attempt(self.db, request, state, platform)

    def test_production_consumption_requires_host_prefixed_cookie(self):
        state, browser, request, _ = self.begin(production=True)
        settings = SimpleNamespace(app_env="production")
        with self.assertRaises(HTTPError):
            self.target.consume_oauth_attempt(self.db, SimpleNamespace(cookies={"dash_oauth_google_ads": browser}), state, "google_ads", settings)
        self.assertEqual(self.target.consume_oauth_attempt(self.db, request, state, "google_ads", settings)["user_id"], "owner-1")

    def test_missing_or_wrong_browser_is_rejected_without_consuming_legitimate_attempt(self):
        state, _, request, _ = self.begin()
        for cookies in ({}, {"dash_oauth_google_ads": secrets.token_urlsafe(32)}):
            with self.assertRaises(HTTPError):
                self.target.consume_oauth_attempt(self.db, SimpleNamespace(cookies=cookies), state, "google_ads")
        self.assertEqual(self.target.consume_oauth_attempt(self.db, request, state, "google_ads")["client_id"], "client-1")

    def test_cross_provider_expiration_and_tampering_rejected(self):
        state, browser, request, _ = self.begin()
        with self.assertRaises(HTTPError):
            self.target.consume_oauth_attempt(self.db, SimpleNamespace(cookies={"dash_oauth_meta_ads": browser}), state, "meta_ads")
        with self.assertRaises(HTTPError):
            self.target.consume_oauth_attempt(self.db, request, "X" + state[1:], "google_ads")
        self.db.execute("UPDATE oauth_attempts SET expires_at=:expired", {"expired": datetime.utcnow() - timedelta(seconds=1)})
        self.db.commit()
        with self.assertRaises(HTTPError):
            self.target.consume_oauth_attempt(self.db, request, state, "google_ads")

    def test_atomic_compare_and_consume_rejects_loser(self):
        state, _, request, _ = self.begin()
        execute = self.db.execute
        def lose_race(sql, params=None):
            if sql.startswith("UPDATE oauth_attempts SET consumed_at"):
                return SimpleNamespace(rowcount=0)
            return execute(sql, params)
        self.db.execute = lose_race
        with self.assertRaises(HTTPError):
            self.target.consume_oauth_attempt(self.db, request, state, "google_ads")
        self.assertIsNone(self.db.connection.execute("SELECT consumed_at FROM oauth_attempts").fetchone()[0])

    def test_finish_expires_correct_cookie_and_disables_cache(self):
        response = SimpleNamespace(delete_cookie=Mock(), headers={})
        result = self.target.finish_oauth(response, "meta_ads", SimpleNamespace(app_env="production"))
        self.assertIs(result, response)
        self.assertEqual(response.delete_cookie.call_args.args[0], "__Host-dash_oauth_meta_ads")
        self.assertEqual(response.delete_cookie.call_args.kwargs["path"], "/")
        self.assertEqual(response.headers["Cache-Control"], "no-store")


class EncryptionContracts(unittest.TestCase):
    def target(self):
        return definitions("scripts/maintenance/migrate_token_encryption.py", ["legacy_key", "rotate_rows", "replace_env_values"],
                           base64=base64, hashlib=hashlib, Fernet=Fernet, MultiFernet=MultiFernet, re=re)

    def test_migrates_legacy_and_preserves_null_refresh_and_plaintext(self):
        target = self.target()
        old = target.legacy_key("dummy-jwt-key")
        new = Fernet.generate_key()
        rows = [{"id": "dummy", "access_token_encrypted": Fernet(old).encrypt(b"dummy-provider-token").decode(),
                 "refresh_token_encrypted": None}]
        result = target.rotate_rows(rows, [old], new)
        self.assertEqual(Fernet(new).decrypt(result[0]["access_token_encrypted"].encode()), b"dummy-provider-token")
        self.assertIsNone(result[0]["refresh_token_encrypted"])
        self.assertNotEqual(result[0]["access_token_encrypted"], rows[0]["access_token_encrypted"])

    def test_migration_can_resume_with_mixed_ciphertexts(self):
        target = self.target()
        old, new = Fernet.generate_key(), Fernet.generate_key()
        rows = [{"id": str(index), "access_token_encrypted": Fernet(key).encrypt(b"dummy").decode(),
                 "refresh_token_encrypted": Fernet(key).encrypt(b"refresh").decode()} for index, key in enumerate((old, new))]
        for row in target.rotate_rows(rows, [old], new):
            self.assertEqual(Fernet(new).decrypt(row["refresh_token_encrypted"].encode()), b"refresh")

    def test_invalid_ciphertext_aborts_preflight(self):
        with self.assertRaises(InvalidToken):
            self.target().rotate_rows([{"id": "dummy", "access_token_encrypted": "corrupted", "refresh_token_encrypted": None}],
                                      [Fernet.generate_key()], Fernet.generate_key())

    def test_environment_update_preserves_jwt_and_unrelated_configuration(self):
        source = "# keep comment\nSECRET_KEY=dummy-jwt\nDATABASE_URL=sqlite:///dummy.db\nTOKEN_ENCRYPTION_KEY=old\n"
        result = self.target().replace_env_values(source, {"TOKEN_ENCRYPTION_KEY": "new", "TOKEN_ENCRYPTION_PREVIOUS_KEYS": "bridge"})
        self.assertIn("SECRET_KEY=dummy-jwt\n", result)
        self.assertIn("# keep comment\n", result)
        self.assertIn("TOKEN_ENCRYPTION_KEY=new", result)
        self.assertNotIn("TOKEN_ENCRYPTION_KEY=old", result)

    def test_independent_key_decrypts_after_jwt_change(self):
        key = Fernet.generate_key().decode()
        settings = SimpleNamespace(token_encryption_key=key, token_encryption_previous_keys="", secret_key="jwt-before", app_env="test")
        target = definitions("app/utils/crypto.py", ["_derive_key_from_secret", "get_fernet", "encrypt_text", "decrypt_text"],
                             hashlib=hashlib, base64=base64, Fernet=Fernet, MultiFernet=MultiFernet,
                             warnings=warnings, get_settings=lambda: settings)
        encrypted = target.encrypt_text("dummy-token")
        settings.secret_key = "jwt-after"
        self.assertEqual(target.decrypt_text(encrypted), "dummy-token")

    def test_backup_round_trip_and_restore_never_overwrites(self):
        target = definitions("scripts/maintenance/database_backup.py", ["private_file", "encrypt_backup", "restore_file", "snapshot_sqlite"],
                             os=os, Path=Path, sqlite3=sqlite3, Fernet=Fernet, MAX_BYTES=128*1024*1024)
        with tempfile.TemporaryDirectory(dir="/scratch") as temp:
            directory = Path(temp)
            db = directory / "source.sqlite"
            with sqlite3.connect(db) as connection:
                connection.execute("CREATE TABLE fixtures (label TEXT)")
                connection.execute("INSERT INTO fixtures VALUES ('dummy')")
            snapshot = directory / "snapshot.sqlite"
            target.snapshot_sqlite(db, snapshot)
            key = Fernet.generate_key()
            encrypted = directory / "backup.fernet"
            encrypted.write_bytes(target.encrypt_backup(snapshot.read_bytes(), key))
            restored = directory / "restored.sqlite"
            target.restore_file(encrypted, restored, key)
            with sqlite3.connect(restored) as connection:
                self.assertEqual(connection.execute("SELECT label FROM fixtures").fetchone()[0], "dummy")
            with self.assertRaises(ValueError):
                target.restore_file(encrypted, restored, key)


class HTTPPolicyContracts(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(rate_limit_enabled=True, auth_requests_per_minute=2,
            ai_requests_per_minute=1, api_requests_per_minute=10, max_request_bytes=8, app_env="production")
        self.target = definitions("app/utils/security_http.py", ["RequestPolicy", "category_for", "SecurityHTTPMiddleware"],
                                  OrderedDict=OrderedDict, time=time, json=json, uuid=uuid, logger=Mock())

    def test_limits_reset_and_separate_clients_and_categories(self):
        policy = self.target.RequestPolicy(self.settings)
        self.assertTrue(policy.admit("ip1", "auth", 0)[0])
        self.assertTrue(policy.admit("ip1", "auth", 1)[0])
        self.assertFalse(policy.admit("ip1", "auth", 2)[0])
        self.assertTrue(policy.admit("ip2", "auth", 2)[0])
        self.assertTrue(policy.admit("ip1", "api", 2)[0])
        self.assertTrue(policy.admit("ip1", "auth", 61)[0])

    def test_saturation_does_not_reset_active_buckets(self):
        policy = self.target.RequestPolicy(self.settings)
        for index in range(10000):
            policy.admit(str(index), "api", 0)
        self.assertFalse(policy.admit("new-ip", "auth", 1)[0])
        self.assertEqual(len(policy.windows), 10000)

    def test_reads_are_not_throttled_as_paid_generation(self):
        self.assertEqual(self.target.category_for("/reports/", "GET"), "api")
        self.assertEqual(self.target.category_for("/reports/demo", "POST"), "ai")
        self.assertEqual(self.target.category_for("/auth/login/", "POST"), "auth")

    def call(self, body, policy=None, path="/clients/", method="POST"):
        messages = []
        called = []
        requests = iter([{"type": "http.request", "body": body, "more_body": False}])
        async def receive():
            return next(requests)
        async def send(message):
            messages.append(message)
        async def app(scope, receive, send):
            called.append((await receive())["body"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        policy = policy or self.target.RequestPolicy(self.settings)
        middleware = self.target.SecurityHTTPMiddleware(app, self.settings, policy)
        complete(middleware({"type": "http", "path": path, "method": method, "client": ("dummy-ip", 1)}, receive, send))
        return messages, called

    def test_body_limit_is_before_route_and_headers_are_present(self):
        messages, called = self.call(b"123456789")
        self.assertEqual(messages[0]["status"], 413)
        self.assertEqual(called, [])
        self.assertEqual(dict(messages[0]["headers"])[b"referrer-policy"], b"no-referrer")

    def test_valid_body_is_forwarded_and_no_store_hsts_and_request_id_set(self):
        messages, called = self.call(b"dummy")
        headers = dict(messages[0]["headers"])
        self.assertEqual(called, [b"dummy"])
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertIn(b"strict-transport-security", headers)
        self.assertEqual(len(headers[b"x-request-id"]), 32)

    def test_throttling_returns_retry_after_without_route(self):
        policy = self.target.RequestPolicy(self.settings)
        self.call(b"", policy, "/reports/demo")
        messages, called = self.call(b"", policy, "/reports/demo")
        self.assertEqual(messages[0]["status"], 429)
        self.assertIn(b"retry-after", dict(messages[0]["headers"]))
        self.assertEqual(called, [])


class ProductionConfigurationContracts(unittest.TestCase):
    def settings(self):
        target = definitions("app/config.py", ["Settings"], BaseSettings=object,
                             model_validator=lambda **kwargs: lambda function: function,
                             base64=base64, hashlib=hashlib, urlsplit=urlsplit)
        settings = target.Settings()
        settings.app_env = "production"
        settings.secret_key = "dummy-jwt-secret-with-at-least-32-characters"
        settings.token_encryption_key = Fernet.generate_key().decode()
        settings.cors_origins = ["https://app.example.test"]
        settings.trusted_hosts = ["api.example.test"]
        settings.frontend_base_url = "https://app.example.test"
        settings.google_ads_redirect_uri = "https://api.example.test/auth/google/callback"
        settings.meta_redirect_uri = "https://api.example.test/auth/meta/callback"
        return settings

    def test_secure_production_settings_accepted(self):
        settings = self.settings()
        self.assertIs(settings.production_guards(), settings)

    def test_missing_or_jwt_derived_encryption_key_rejected(self):
        for value in ("", base64.urlsafe_b64encode(hashlib.sha256(b"dummy-jwt-secret-with-at-least-32-characters").digest()).decode()):
            settings = self.settings()
            settings.token_encryption_key = value
            with self.assertRaises(ValueError):
                settings.production_guards()

    def test_http_wildcard_hosts_disabled_limits_and_short_jwt_rejected(self):
        for attribute, value in (("frontend_base_url", "http://app.example.test"), ("trusted_hosts", ["*"]),
                                 ("rate_limit_enabled", False), ("secret_key", "short")):
            settings = self.settings()
            setattr(settings, attribute, value)
            with self.assertRaises(ValueError):
                settings.production_guards()


if __name__ == "__main__":
    unittest.main()
