"""Offline regression tests: no local database or real provider credentials."""
import os
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "offline-test-secret"
os.environ["APP_ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.client import Client
from app.models.campaign import Campaign
from app.models.integration import ClientIntegration
from app.utils.auth import get_current_user
from app.utils.meta_ads import MetaAdsService
from app.utils.google_ads import GoogleAdsService


class CampaignFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(id="u1", email="one@example.test", password_hash="unused")
        self.db.add_all([self.user, User(id="u2", email="two@example.test", password_hash="unused")])
        self.db.add_all([Client(id="c1", name="One", user_id="u1"),
                         Client(id="c2", name="Two", user_id="u1"),
                         Client(id="c3", name="Other user", user_id="u2")])
        self.integration = ClientIntegration(id="i1", client_id="c1", platform="meta_ads",
                                            account_id="act_1", status="connected", access_token_encrypted="unused")
        self.db.add(self.integration)
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.http = TestClient(app)

    def tearDown(self):
        self.http.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def campaign(self, external_id, client="c1", integration=None):
        row = Campaign(client_id=client, integration_id=integration, platform="meta_ads",
                       external_id=external_id, name=external_id, spend=10)
        self.db.add(row)
        self.db.commit()
        return row

    def test_empty_and_legacy_mocks_are_not_returned_or_deleted(self):
        self.campaign("meta_ads_c1_0")
        self.assertEqual(self.http.get("/campaigns/").json(), [])
        summary = self.http.get("/campaigns/summary").json()
        self.assertEqual(summary["total_spend"], 0)
        self.assertEqual(summary["campaign_count"], 0)
        self.assertEqual(self.db.query(Campaign).count(), 1)
        self.assertEqual(self.http.post("/integrations/i1/mock").status_code, 404)

    def test_client_filter_and_ownership(self):
        self.campaign("meta_1")
        self.campaign("meta_2", "c2")
        self.campaign("meta_3", "c3")
        self.assertEqual(len(self.http.get("/campaigns/").json()), 2)
        rows = self.http.get("/campaigns/?client_id=c2").json()
        self.assertEqual([r["client_id"] for r in rows], ["c2"])
        for path in ("/campaigns/?client_id=c3", "/campaigns/summary?client_id=c3"):
            self.assertEqual(self.http.get(path).status_code, 404)

    def test_meta_sync_persists_updates_and_empty_snapshot_hides_stale_rows(self):
        payload = dict(external_id="meta_100", platform_account_id="act_1", name="Real",
                       status="archived", objective="sales", spend=12, clicks=4,
                       impressions=100, conversions=1.5, start_date="2026-09-01", end_date=None)
        with patch("app.routers.integration._token", return_value="test-token"), patch(
            "app.routers.integration._meta_service"
        ) as service:
            service.return_value.fetch_campaigns.return_value = [payload]
            self.assertEqual(self.http.post("/integrations/i1/sync").status_code, 200)
            self.assertEqual(self.http.post("/integrations/i1/sync").status_code, 200)
            self.assertEqual(self.db.query(Campaign).count(), 1)
            row = self.http.get("/campaigns/").json()[0]
            self.assertEqual(row["conversions"], 1.5)
            self.assertEqual(row["start_date"], "2026-09-01")
            service.return_value.fetch_campaigns.return_value = []
            self.assertEqual(self.http.post("/integrations/i1/sync").json()["synced_campaigns"], 0)
            self.assertEqual(self.http.get("/campaigns/").json(), [])
            self.assertEqual(self.db.query(Campaign).count(), 1)

    def test_sync_failure_is_not_success_and_preserves_last_sync(self):
        self.campaign("meta_existing", integration="i1")
        with patch("app.routers.integration._token", return_value="test"), patch(
            "app.routers.integration._meta_service"
        ) as service:
            service.return_value.fetch_campaigns.side_effect = RuntimeError("secret-test-token")
            response = self.http.post("/integrations/i1/sync")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-test-token", response.text)
        self.assertIsNone(self.integration.last_sync_at)
        self.assertEqual(len(self.http.get("/campaigns/").json()), 1)

    def test_meta_account_selection_validates_provider_membership(self):
        with patch("app.routers.integration._accounts", return_value=["act_1"]):
            self.assertEqual(self.http.get("/integrations/i1/accounts").json(), {"accounts": ["act_1"]})
            self.assertEqual(self.http.put("/integrations/i1", json={"account_id": "act_other"}).status_code, 400)
            self.assertEqual(self.http.put("/integrations/i1", json={"account_id": "act_1"}).status_code, 200)
        self.integration.account_id = None
        self.db.commit()
        self.assertEqual(self.http.post("/integrations/i1/sync").status_code, 400)

    def test_other_user_cannot_sync_or_list_accounts(self):
        self.user = self.db.get(User, "u2")
        self.assertEqual(self.http.post("/integrations/i1/sync").status_code, 404)
        self.assertEqual(self.http.get("/integrations/i1/accounts").status_code, 404)

    def test_google_missing_config_does_not_generate_demo(self):
        self.integration.platform = "google_ads"
        self.db.commit()
        with patch("app.routers.integration.get_settings", return_value=SimpleNamespace(
            google_ads_developer_token="", google_ads_client_id="", google_ads_client_secret=""
        )):
            self.assertEqual(self.http.post("/integrations/i1/sync").status_code, 400)
        self.assertEqual(self.db.query(Campaign).count(), 0)


class ProviderTests(unittest.TestCase):
    def test_google_config_omits_developer_token_and_pins_supported_api(self):
        with patch("app.utils.google_ads.GoogleAdsClient.load_from_dict") as load:
            GoogleAdsService("client", "secret")._get_client("refresh")
        config = load.call_args.args[0]
        self.assertNotIn("developer_token", config)
        self.assertEqual(config["refresh_token"], "refresh")
        self.assertEqual(load.call_args.kwargs["version"], "v26")

    def test_google_sdk_builds_customer_service_without_developer_token(self):
        from google.oauth2.credentials import Credentials
        # Avoid the SDK's initial OAuth refresh: no network or real credentials.
        with patch("google.ads.googleads.oauth2.get_credentials", return_value=Credentials("offline")):
            sdk = GoogleAdsService("client", "secret")._get_client("refresh")
        self.assertIsNone(sdk.developer_token)
        service = sdk.get_service("CustomerService")
        self.assertIn(".v26.", type(service).__module__)
        service.transport.close()

    def test_google_service_needs_only_oauth_credentials(self):
        from app.routers.integration import _google_service
        with patch("app.routers.integration.get_settings", return_value=SimpleNamespace(
            google_ads_client_id="client", google_ads_client_secret="secret"
        )):
            self.assertIsInstance(_google_service(), GoogleAdsService)

    def test_google_account_listing_maps_resource_names(self):
        with patch.object(GoogleAdsService, "_get_client") as client:
            client.return_value.get_service.return_value.list_accessible_customers.return_value = SimpleNamespace(
                resource_names=["customers/123", "customers/456"]
            )
            self.assertEqual(GoogleAdsService("client", "secret").list_accessible_customers("refresh"), ["123", "456"])

    def test_meta_pagination_and_metric_mapping(self):
        def response(data):
            result = Mock()
            result.json.return_value = data
            return result
        service = MetaAdsService("app", "secret", "callback")
        pages = [
            response({"data": [{"id": "1", "status": "ARCHIVED", "daily_budget": "500"}],
                      "paging": {"next": "unused", "cursors": {"after": "next-cursor"}}}),
            response({"data": [{"id": "2", "status": "ACTIVE", "start_time": "2026-09-01T00:00:00+0000"}]}),
            response({"data": [{"campaign_id": "1", "spend": "20", "clicks": "10", "impressions": "100",
                      "actions": [{"action_type": "purchase", "value": "2"},
                                  {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "2"},
                                  {"action_type": "lead", "value": "1"}]}]}),
        ]
        with patch("app.utils.meta_ads.requests.get", side_effect=pages) as get:
            rows = service.fetch_campaigns("private-token", "1")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["conversions"], 3)
        self.assertEqual(rows[0]["report_metrics"]["leads"], 1)
        self.assertEqual(rows[0]["report_metrics"]["purchases"], 2)
        self.assertNotIn("conversions", rows[0]["report_metrics"])
        self.assertEqual(rows[1]["report_metrics"], {})
        self.assertEqual(rows[0]["daily_budget"], 5)
        self.assertEqual(rows[0]["budget"], 0)
        self.assertEqual(rows[0]["cpc"], 2)
        self.assertEqual(rows[1]["spend"], 0)
        self.assertEqual(rows[1]["start_date"], date(2026, 9, 1))
        self.assertNotIn("access_token", get.call_args.kwargs["params"])
        self.assertEqual(get.call_args.kwargs["timeout"], 30)

    def test_meta_failure_has_no_credentials_in_message(self):
        with patch("app.utils.meta_ads.requests.get", side_effect=requests.Timeout("secret-url")):
            with self.assertRaises(RuntimeError) as error:
                MetaAdsService("", "", "").fetch_ad_accounts("token")
        self.assertNotIn("secret-url", str(error.exception))

    def test_google_provider_failure_propagates(self):
        with patch.object(GoogleAdsService, "_get_client") as client:
            client.return_value.get_service.return_value.search.side_effect = RuntimeError("provider failure")
            with self.assertRaises(RuntimeError):
                GoogleAdsService("", "").fetch_campaigns("123", "token")


if __name__ == "__main__":
    unittest.main()
