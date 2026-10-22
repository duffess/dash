"""Offline maintenance: preserve provider tokens while separating JWT/encryption.

Stop the backend before --apply. Default is read/verify only. Never prints keys,
database URLs, provider tokens or exception text. An interrupted apply leaves a
bridge keyring so both old and new ciphertexts remain readable on retry.
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import secrets
import sqlite3
import tempfile
from datetime import datetime, timezone
from cryptography.fernet import Fernet, MultiFernet
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def legacy_key(secret):
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def rotate_rows(rows, old_keys, new_key):
    reader = MultiFernet([Fernet(new_key), *(Fernet(key) for key in old_keys)])
    writer = Fernet(new_key)
    result = []
    for row in rows:
        values = dict(row)
        for field in ("access_token_encrypted", "refresh_token_encrypted"):
            token = row[field]
            if token is not None:
                plain = reader.decrypt(token.encode())
                rotated = writer.encrypt(plain)
                if writer.decrypt(rotated) != plain:
                    raise RuntimeError("Rotation verification failed")
                values[field] = rotated.decode()
        result.append(values)
    return result


def replace_env_values(source, updates):
    for name, value in updates.items():
        line = name + "=" + value
        pattern = re.compile(r"^\s*(?:export\s+)?" + re.escape(name) + r"\s*=.*$", re.MULTILINE)
        if pattern.search(source):
            source = pattern.sub(lambda match: line, source)
        else:
            source = source.rstrip() + "\n" + line + "\n"
    return source


def atomic_private_write(path, content):
    path = Path(path)
    descriptor, temp = tempfile.mkstemp(prefix=".dash-secret-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--key-file", type=Path, required=True, help="Private persistent destination for the new key")
    parser.add_argument("--backup-dir", type=Path, required=True, help="Private directory outside repository")
    parser.add_argument("--postgres-backup", type=Path, help="Previously verified fresh pg_dump, required for PostgreSQL")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backend-stopped", action="store_true", help="Confirm all backend workers are stopped")
    parser.add_argument("--rotate-jwt", action="store_true", help="Also replace JWT secret after token migration; logs users out")
    args = parser.parse_args()
    env_path = args.env_file.resolve()
    original = env_path.read_text(encoding="utf-8-sig")
    config = dotenv_values(stream=__import__("io").StringIO(original), interpolate=False)
    url = make_url(config["DATABASE_URL"])
    if url.get_backend_name() == "sqlite":
        if not url.database or url.database == ":memory:":
            raise ValueError("Existing persistent SQLite required")
        sqlite_path = Path(url.database)
        if not sqlite_path.is_absolute():
            sqlite_path = env_path.parent / sqlite_path
        if not sqlite_path.is_file():
            raise ValueError("SQLite source missing; no empty database will be created")
        url = url.set(database=str(sqlite_path.resolve()))
    old_primary = config.get("TOKEN_ENCRYPTION_KEY", "").strip()
    old_keys = [old_primary.encode() if old_primary else legacy_key(config["SECRET_KEY"])]
    old_keys += [key.strip().encode() for key in config.get("TOKEN_ENCRYPTION_PREVIOUS_KEYS", "").split(",") if key.strip()]
    if args.key_file.exists():
        new_key = args.key_file.read_bytes().strip()
        Fernet(new_key)
    else:
        new_key = Fernet.generate_key()
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(text("SELECT id, access_token_encrypted, refresh_token_encrypted FROM client_integrations")).mappings()]
        rotated = rotate_rows(rows, old_keys, new_key)
        if not args.apply:
            print(f"VERIFICADO: {len(rows)} integrações legíveis. Nenhuma alteração. Use --apply com backend parado.")
            return
        if not args.backend_stopped:
            raise ValueError("Stop every backend worker and confirm --backend-stopped")
        backup = args.backup_dir.resolve()
        repo = Path(__file__).resolve().parents[2]
        if backup == repo or repo in backup.parents or backup == env_path.parent:
            raise ValueError("Use private backup directory outside repository")
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        if url.get_backend_name() == "sqlite":
            if not url.database or url.database == ":memory:":
                raise ValueError("Persistent SQLite required")
            with sqlite3.connect(url.database) as source, sqlite3.connect(backup / ("before-token-migration-" + timestamp + ".sqlite")) as destination:
                source.backup(destination)
                if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup verification failed")
        elif url.get_backend_name() == "postgresql":
            if not args.postgres_backup or not args.postgres_backup.is_file() or args.postgres_backup.stat().st_size == 0:
                raise ValueError("Verified PostgreSQL backup required")
        else:
            raise ValueError("Unsupported database")
        atomic_private_write(backup / ("before-token-migration-" + timestamp + ".env"), original)
        args.key_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not args.key_file.exists():
            descriptor = os.open(args.key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(new_key + b"\n")
        bridge = replace_env_values(original, {"TOKEN_ENCRYPTION_KEY": new_key.decode(),
                    "TOKEN_ENCRYPTION_PREVIOUS_KEYS": ",".join(dict.fromkeys(key.decode() for key in old_keys))})
        # Bridge first: if the process stops after DB commit, neither format is lost.
        atomic_private_write(env_path, bridge)
        with engine.begin() as connection:
            for old, new in zip(rows, rotated):
                refresh_condition = "refresh_token_encrypted IS NULL" if old["refresh_token_encrypted"] is None else "refresh_token_encrypted=:old_refresh"
                result = connection.execute(text("UPDATE client_integrations SET access_token_encrypted=:access, refresh_token_encrypted=:refresh "
                    "WHERE id=:id AND access_token_encrypted=:old_access AND " + refresh_condition),
                    {"id": old["id"], "access": new["access_token_encrypted"], "refresh": new["refresh_token_encrypted"],
                     "old_access": old["access_token_encrypted"], "old_refresh": old["refresh_token_encrypted"]})
                if result.rowcount != 1:
                    raise RuntimeError("Concurrent token change. Stop backend before retry")
            # Verify ALL rows, including unexpected inserts, before dropping old keys.
            for row in connection.execute(text("SELECT access_token_encrypted, refresh_token_encrypted FROM client_integrations")).mappings():
                for value in row.values():
                    if value is not None:
                        Fernet(new_key).decrypt(value.encode())
        final = {"TOKEN_ENCRYPTION_PREVIOUS_KEYS": ""}
        if args.rotate_jwt:
            final["SECRET_KEY"] = secrets.token_urlsafe(48)
        atomic_private_write(env_path, replace_env_values(bridge, final))
        print(f"CONCLUÍDO: {len(rows)} integrações recriptografadas e verificadas. Backup privado preservado.")
        print("JWT rotacionado: faça login novamente." if args.rotate_jwt else "JWT não alterado.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("Migração interrompida. Não altere SECRET_KEY nem remova o key-file. Revise configuração, backup e retente com backend parado.") from None
