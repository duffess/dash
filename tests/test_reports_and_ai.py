"""Offline AI/report integration tests; all provider calls are replaced."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException
import openai

import test_campaign_sync as campaign_fixtures
from app.models.insight import Insight
from app.models.report import Report
from app.utils.ai import generate_analysis


class ReportFlowTests(unittest.TestCase):
    setUp = campaign_fixtures.CampaignFlowTests.setUp
    tearDown = campaign_fixtures.CampaignFlowTests.tearDown
    campaign = campaign_fixtures.CampaignFlowTests.campaign

    def test_empty_or_mock_data_cannot_generate_insight_or_report(self):
        self.campaign("meta_ads_c1_0")
        with patch("app.routers.insight.generate_analysis") as ai:
            self.assertEqual(self.http.post("/insights/c1/generate").status_code, 400)
            ai.assert_not_called()
        self.assertEqual(self.http.post("/reports/", json={"client_id": "c1"}).status_code, 400)
        self.assertEqual(self.db.query(Report).count(), 0)
        self.assertEqual(self.db.query(Insight).count(), 0)

    def test_metric_report_needs_no_ai_and_snapshot_survives_updates(self):
        campaign = self.campaign("meta_1")
        with patch("app.routers.report.generate_analysis") as ai:
            response = self.http.post("/reports/", json={"client_id": "c1", "title": "  Mensal  "})
            ai.assert_not_called()
        self.assertEqual(response.status_code, 201, response.text)
        report = response.json()
        self.assertEqual(report["title"], "Mensal")
        self.assertEqual(report["snapshot"]["campaigns"][0]["spend"], 10)
        campaign.spend = 99
        self.db.commit()
        saved = self.http.get("/reports/" + report["id"]).json()
        self.assertEqual(saved["snapshot"]["campaigns"][0]["spend"], 10)
        self.assertEqual(saved["analysis"], None)
        self.assertEqual(len(self.http.get("/reports/?client_id=c1").json()), 1)
        self.assertEqual(self.http.get("/reports/?client_id=c2").json(), [])

    def test_ai_failure_saves_neither_report_nor_insight(self):
        self.campaign("meta_1")
        for route, target, payload in [
            ("/insights/c1/generate", "app.routers.insight.generate_analysis", None),
            ("/reports/", "app.routers.report.generate_analysis", {"client_id": "c1", "include_ai": True}),
        ]:
            with patch(target, side_effect=HTTPException(status_code=503, detail="IA indisponível")):
                self.assertEqual(self.http.post(route, json=payload).status_code, 503)
        self.assertEqual(self.db.query(Report).count(), 0)
        self.assertEqual(self.db.query(Insight).count(), 0)

    def test_reuse_insight_keeps_original_data_without_second_ai_call(self):
        campaign = self.campaign("meta_1")
        with patch("app.routers.insight.generate_analysis", return_value=("Diagnóstico verificado", "test-model")):
            insight = self.http.post("/insights/c1/generate").json()
        campaign.spend = 99
        self.db.commit()
        with patch("app.routers.report.generate_analysis") as ai:
            response = self.http.post("/reports/", json={"client_id": "c1", "insight_id": insight["id"]})
            ai.assert_not_called()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["snapshot"]["campaigns"][0]["spend"], 10)
        self.assertEqual(response.json()["analysis"], "Diagnóstico verificado")
        self.assertEqual(self.http.post("/reports/", json={"client_id": "c2", "insight_id": insight["id"]}).status_code, 404)

    def test_generate_report_with_ai_also_saves_insight(self):
        self.campaign("meta_1")
        with patch("app.routers.report.generate_analysis", return_value=("Resultado", "test-model")):
            result = self.http.post("/reports/", json={"client_id": "c1", "include_ai": True})
        self.assertEqual(result.status_code, 201)
        self.assertTrue(result.json()["has_analysis"])
        self.assertEqual(self.http.get("/insights/c1").json()[0]["content"], "Resultado")

    def test_report_and_insight_ownership_enforced(self):
        self.campaign("meta_1", "c3")
        self.assertEqual(self.http.post("/reports/", json={"client_id": "c3"}).status_code, 404)
        self.assertEqual(self.http.get("/reports/preview?client_id=c3").status_code, 404)
        self.assertEqual(self.http.post("/insights/c3/generate").status_code, 404)
        self.campaign("meta_2")
        report = self.http.post("/reports/", json={"client_id": "c1"}).json()
        from app.models.user import User
        self.user = self.db.get(User, "u2")
        self.assertEqual(self.http.get("/reports/").json(), [])
        self.assertEqual(self.http.get("/reports/" + report["id"]).status_code, 404)
        self.assertEqual(self.http.get("/reports/" + report["id"] + "/html").status_code, 404)

    def test_exports_escape_untrusted_text(self):
        row = self.campaign("meta_1")
        row.name = '<script>alert("x")</script>'
        self.db.commit()
        with patch("app.routers.report.generate_analysis", return_value=('<img src=x onerror="alert(1)">', "test")):
            report = self.http.post("/reports/", json={"client_id": "c1", "title": "<script>title</script>", "include_ai": True}).json()
        response = self.http.get("/reports/" + report["id"] + "/html")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>", response.text)
        self.assertNotIn("<img ", response.text)
        self.assertIn("&lt;script&gt;", response.text)
        self.assertIn("Últimos 30 dias", response.text)
        self.assertIn("attachment;", response.headers["content-disposition"])

    def test_legacy_insights_without_evidence_are_not_shown(self):
        self.db.add(Insight(client_id="c1", content="Old configuration error"))
        self.db.commit()
        self.assertEqual(self.http.get("/insights/c1").json(), [])
        self.assertEqual(self.http.get("/campaigns/insights").json(), [])

    def test_ai_configuration_status_does_not_expose_key(self):
        with patch("app.routers.insight.get_settings", return_value=SimpleNamespace(openai_api_key="secret", openai_model="test", demo_ai_enabled=False)):
            response = self.http.get("/insights/status")
        self.assertTrue(response.json()["configured"])
        self.assertFalse(response.json()["demo_ai_enabled"])
        self.assertNotIn("secret", response.text)


class AIServiceTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "period_days": 30, "period_note": "Janela de 30 dias", "currency_note": "Moedas desconhecidas",
            "conversion_note": "Atribuição varia", "accounts": [],
            "campaigns": [{"name": "Campanha", "impressions": 100, "clicks": 1, "spend": 3, "conversions": 0}],
        }
        self.settings = patch("app.utils.ai.get_settings", return_value=SimpleNamespace(openai_api_key="fake-key", openai_model="gpt-4o-mini"))
        self.settings.start()
        self.addCleanup(self.settings.stop)

    def test_missing_key_is_error_not_content(self):
        with patch("app.utils.ai.get_settings", return_value=SimpleNamespace(openai_api_key="")):
            with self.assertRaises(HTTPException) as error:
                generate_analysis(self.snapshot)
        self.assertEqual(error.exception.status_code, 503)

    def test_zero_metrics_do_not_call_provider(self):
        self.snapshot["campaigns"] = [dict(name="Empty", impressions=0, clicks=0, spend=0, conversions=0)]
        with patch("app.utils.ai.openai.OpenAI") as client:
            with self.assertRaises(HTTPException):
                generate_analysis(self.snapshot)
            client.assert_not_called()

    def test_provider_success_and_truncation(self):
        with patch("app.utils.ai.openai.OpenAI") as client:
            provider = client.return_value.__enter__.return_value
            choice = SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content="Análise", refusal=None))
            provider.chat.completions.create.return_value = SimpleNamespace(choices=[choice])
            self.assertEqual(generate_analysis(self.snapshot), ("Análise", "gpt-4o-mini"))
            kwargs = provider.chat.completions.create.call_args.kwargs
            self.assertFalse(kwargs["store"])
            self.assertIn("period_days", kwargs["messages"][1]["content"])
            choice.finish_reason = "length"
            with self.assertRaises(HTTPException):
                generate_analysis(self.snapshot)

    def test_provider_error_is_sanitized(self):
        with patch("app.utils.ai.openai.OpenAI") as client:
            client.return_value.__enter__.return_value.chat.completions.create.side_effect = openai.OpenAIError("private-token")
            with self.assertRaises(HTTPException) as error:
                generate_analysis(self.snapshot)
        self.assertEqual(error.exception.status_code, 502)
        self.assertNotIn("private-token", error.exception.detail)


if __name__ == "__main__":
    unittest.main()
