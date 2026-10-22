import unittest
from copy import deepcopy
from unittest.mock import patch
from types import SimpleNamespace

import test_campaign_sync as fixtures
from app.models.report import Report
from app.models.campaign import Campaign
from app.models.insight import Insight
from app.utils.report_metrics import metrics, enrich_snapshot
from app.utils.report_demo import demo_snapshot
from app.utils.ai import generate_analysis


class DynamicMetricTests(unittest.TestCase):
    def test_missing_is_not_zero_and_zero_denominator_has_no_ratio(self):
        result = metrics({"spend": 100, "leads": 0, "clicks": 0, "impressions": 100})
        self.assertEqual(result["leads"], 0)
        self.assertEqual(result["ctr"], 0)
        for key in ("cpl", "cpc", "revenue", "roas", "purchases"):
            self.assertNotIn(key, result)

    def test_ratios_and_invalid_numbers(self):
        self.assertEqual(metrics({"spend": 100, "leads": 5})["cpl"], 20)
        self.assertEqual(metrics({"spend": 100, "revenue": 400})["roas"], 4)
        self.assertEqual(metrics({"spend": float('nan'), "clicks": -1, "leads": True}), {})

    def test_partial_account_totals_are_not_presented_as_complete(self):
        data = demo_snapshot("limited")
        self.assertNotIn("spend", data["accounts"][0]["metrics"])
        self.assertNotIn("clicks", data["accounts"][0]["metrics"])
        self.assertEqual(data["accounts"][0]["metrics"]["impressions"], 25000)
        self.assertEqual(data["comparisons"], [])

    def test_enrichment_is_immutable_and_idempotent(self):
        original = demo_snapshot("sales")
        before = deepcopy(original)
        self.assertEqual(enrich_snapshot(original), before)
        self.assertEqual(original, before)

    def test_comparisons_need_same_currency_and_positive_baseline(self):
        data = demo_snapshot("leads")
        data["previous_period"]["campaigns"][0]["currency"] = "USD"
        data["previous_period"]["campaigns"][1]["metrics"]["leads"] = 0
        comparisons = enrich_snapshot(data)["comparisons"]
        self.assertFalse(any(c["campaign"] == data["campaigns"][0]["name"] for c in comparisons))
        self.assertFalse(any(c["metric"] == "leads" for c in comparisons))

    def test_ai_receives_only_available_metrics_and_demo_label(self):
        with patch("app.utils.ai.get_settings", return_value=SimpleNamespace(openai_api_key="test", openai_model="gpt-4o-mini")), patch("app.utils.ai.openai.OpenAI") as client:
            provider = client.return_value.__enter__.return_value
            provider.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
                finish_reason="stop", message=SimpleNamespace(content="Dados fictícios", refusal=None))])
            generate_analysis(demo_snapshot("limited"))
            import json
            evidence = json.loads(provider.chat.completions.create.call_args.kwargs["messages"][1]["content"])
            self.assertEqual(evidence["source"], "demo")
            self.assertNotIn("revenue", evidence["campaigns"][0]["metrics"])
            self.assertNotIn("spend", evidence["campaigns"][0]["metrics"])


class DemoReportFlowTests(unittest.TestCase):
    setUp = fixtures.CampaignFlowTests.setUp
    tearDown = fixtures.CampaignFlowTests.tearDown
    campaign = fixtures.CampaignFlowTests.campaign

    def test_demo_scenarios_are_isolated_and_do_not_call_ai_by_default(self):
        with patch("app.routers.report.generate_analysis") as ai:
            for scenario in ("leads", "sales", "limited", "zero"):
                response = self.http.post("/reports/demo", json={"scenario": scenario})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["snapshot"]["source"], "demo")
                self.assertIn("DADOS FICTÍCIOS", response.json()["rendered_html"])
                self.assertIsNone(response.json()["analysis"])
            ai.assert_not_called()
        for model in (Report, Campaign, Insight):
            self.assertEqual(self.db.query(model).count(), 0)

    def test_demo_ai_is_explicit_and_never_saved_to_real_history(self):
        with patch("app.routers.report.get_settings", return_value=SimpleNamespace(demo_ai_enabled=True)), patch("app.routers.report.generate_analysis", return_value=("Somente demonstração", "test")) as ai:
            response = self.http.post("/reports/demo", json={"scenario": "leads", "include_ai": True})
        self.assertEqual(response.status_code, 200)
        ai.assert_called_once()
        self.assertEqual(self.db.query(Insight).count(), 0)
        self.assertEqual(self.http.get("/reports/").json(), [])

    def test_demo_ai_disabled_on_server_even_if_request_enables_it(self):
        with patch("app.routers.report.get_settings", return_value=SimpleNamespace(demo_ai_enabled=False)), patch("app.routers.report.generate_analysis") as ai:
            response = self.http.post("/reports/demo", json={"scenario": "leads", "include_ai": True})
        self.assertEqual(response.status_code, 403)
        ai.assert_not_called()
        self.assertEqual(self.db.query(Insight).count(), 0)

    def test_demo_rejects_arbitrary_data_and_requires_auth(self):
        self.assertEqual(self.http.post("/reports/demo", json={"scenario": "injected"}).status_code, 422)
        self.assertEqual(self.http.post("/reports/demo", json={"campaigns": []}).status_code, 422)
        from app.main import app
        from app.utils.auth import get_current_user
        app.dependency_overrides.pop(get_current_user)
        self.assertEqual(self.http.post("/reports/demo", json={}).status_code, 401)

    def test_real_report_preserves_explicit_missing_fields(self):
        row = self.campaign("real")
        row.report_metrics = {"impressions": 10, "clicks": 0}
        self.db.commit()
        report = self.http.post("/reports/", json={"client_id": "c1"}).json()
        values = report["snapshot"]["campaigns"][0]["metrics"]
        self.assertEqual(values["clicks"], 0)
        self.assertNotIn("spend", values)
        self.assertNotIn("roas", values)
        self.assertEqual(report["snapshot"]["source"], "synced")
        self.assertNotIn("DADOS FICTÍCIOS", report["rendered_html"])


if __name__ == '__main__':
    unittest.main()
