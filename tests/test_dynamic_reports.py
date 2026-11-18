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
    def test_adaptive_dot_scale_is_bounded_and_handles_partial_values(self):
        from app.utils.report_export import dot_scale, render_report_html
        from datetime import datetime, timezone
        self.assertEqual(dot_scale(150), 1)
        self.assertEqual(dot_scale(1000), 10)
        self.assertLessEqual(__import__('math').ceil(10**8 / dot_scale(10**8)), 150)
        data = demo_snapshot('leads')
        data['campaigns'] = data['campaigns'][:1]
        data['campaigns'][0]['metrics']['leads'] = 1025
        report = SimpleNamespace(title='Teste', snapshot=data, created_at=datetime.now(timezone.utc), analysis=None, ai_model=None)
        html = render_report_html(report)
        self.assertIn('1 ponto completo = 10 leads', html)
        self.assertIn('--fill:50.0000%', html)
        self.assertIn('1.025 leads', html)

    def test_zero_and_missing_metrics_do_not_invent_leads(self):
        from app.utils.report_export import render_report_html
        from datetime import datetime, timezone
        for scenario in ('zero', 'limited'):
            data = demo_snapshot(scenario)
            if scenario == 'zero':
                data['campaigns'][1]['metrics']['leads'] = 0
            report = SimpleNamespace(title='Teste', snapshot=data, created_at=datetime.now(timezone.utc), analysis=None, ai_model=None)
            html = render_report_html(report)
            self.assertIn('DADOS FICTÍCIOS', html)
            if scenario == 'zero':
                self.assertIn('Nenhum resultado registrado', html)
            else:
                self.assertNotIn('leads no período', html)

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

    def test_agency_notes_are_saved_escaped_and_restored(self):
        row = self.campaign('notas')
        row.report_metrics = {'leads': 5, 'spend': 50}
        self.db.commit()
        response = self.http.post('/reports/', json={'client_id':'c1', 'campaign_metrics':{row.id:['leads','spend']}, 'agency_analysis':'Resultado <script>alert(1)</script>', 'next_steps':'Revisar públicos'})
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertIn('Resultado &lt;script&gt;', result['rendered_html'])
        self.assertNotIn('<script>alert(1)</script>', result['rendered_html'])
        loaded = self.http.get('/reports/' + result['id']).json()
        self.assertEqual(loaded['snapshot']['next_steps'], 'Revisar públicos')
        self.assertIn('Revisar públicos', loaded['rendered_html'])

    def test_history_date_filter_and_invalid_range(self):
        row = self.campaign('data')
        self.db.commit()
        created = self.http.post('/reports/', json={'client_id':'c1', 'campaign_metrics':{row.id:['clicks']}})
        self.assertEqual(created.status_code, 201, created.text)
        day = created.json()['created_at'][:10]
        response = self.http.get('/reports/', params={'created_from': day, 'created_to': day})
        self.assertEqual([r['id'] for r in response.json()], [created.json()['id']])
        self.assertEqual(self.http.get('/reports/', params={'created_from':'2030-01-01', 'created_to':'2020-01-01'}).status_code, 422)

    def test_report_branding_persists_and_invalid_logo_is_rejected(self):
        row = self.campaign('marca')
        self.db.commit()
        payload = {'client_id':'c1', 'campaign_metrics':{row.id:['clicks']}, 'agency_name':'Agência <Teste>', 'agency_logo':'data:image/png;base64,iVBORw0KGgo='}
        response = self.http.post('/reports/', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIn('Agência &lt;Teste&gt;', response.json()['rendered_html'])
        self.assertEqual(self.http.get('/reports/' + response.json()['id']).json()['snapshot']['agency_name'], 'Agência <Teste>')
        payload['agency_logo'] = 'data:image/svg+xml;base64,PHN2Zz4='
        self.assertEqual(self.http.post('/reports/', json=payload).status_code, 422)

    def test_client_brand_and_color_are_saved_and_validated(self):
        row = self.campaign('marca-cliente')
        payload = {'client_id': 'c1', 'campaign_metrics': {row.id: ['clicks']}, 'client_logo': 'data:image/png;base64,iVBORw0KGgo=', 'accent_color': '#ab1234'}
        response = self.http.post('/reports/', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        report = self.http.get('/reports/' + response.json()['id']).json()
        self.assertEqual(report['snapshot']['accent_color'], '#ab1234')
        self.assertIn('alt="Logo do cliente"', report['rendered_html'])
        self.assertIn('--report-accent:#ab1234', report['rendered_html'])
        payload['accent_color'] = 'red; background: url(x)'
        self.assertEqual(self.http.post('/reports/', json=payload).status_code, 422)
        payload['accent_color'] = '#123456'
        payload['client_logo'] = 'data:image/svg+xml;base64,PHN2Zz4='
        self.assertEqual(self.http.post('/reports/', json=payload).status_code, 422)

    def test_search_and_delete_report_respect_ownership(self):
        row = self.campaign('busca')
        payload = {'client_id': 'c1', 'campaign_metrics': {row.id: ['clicks']}, 'title': 'Campanha 100% especial'}
        created = self.http.post('/reports/', json=payload).json()
        self.assertEqual(len(self.http.get('/reports/', params={'search': '100%'}).json()), 1)
        self.assertEqual(self.http.get('/reports/', params={'search': '_'}).json(), [])
        self.user = self.db.get(__import__('app.models.user', fromlist=['User']).User, 'u2')
        self.assertEqual(self.http.delete('/reports/' + created['id']).status_code, 404)
        self.user = self.db.get(__import__('app.models.user', fromlist=['User']).User, 'u1')
        self.assertEqual(self.http.delete('/reports/' + created['id']).status_code, 204)
        self.assertEqual(self.http.get('/reports/' + created['id']).status_code, 404)

    def test_preview_is_not_saved_and_is_scoped(self):
        row = self.campaign('previa')
        payload = {'client_id': 'c1', 'campaign_metrics': {row.id: ['clicks']}, 'title': 'Prévia'}
        response = self.http.post('/reports/?preview_only=true', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['id'], 'preview')
        self.assertEqual(self.db.query(Report).count(), 0)
        payload['client_id'] = 'c3'
        self.assertEqual(self.http.post('/reports/?preview_only=true', json=payload).status_code, 404)

    def test_custom_demo_is_isolated_and_validated(self):
        payload = {'scenario': 'leads', 'client_name': 'Meu exemplo', 'title': 'Teste', 'campaign_metrics': {'demo-0': ['leads']}, 'agency_analysis': 'Texto <teste>', 'accent_color': '#112233'}
        response = self.http.post('/reports/demo', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['snapshot']['client_name'], 'Meu exemplo [FICTÍCIO]')
        self.assertEqual(len(body['snapshot']['campaigns']), 1)
        self.assertIn('Texto &lt;teste&gt;', body['rendered_html'])
        self.assertEqual(self.db.query(Report).count(), 0)
        payload['campaign_metrics'] = {'other': ['leads']}
        self.assertEqual(self.http.post('/reports/demo', json=payload).status_code, 422)

    def test_client_overview_is_scoped_to_owner(self):
        self.campaign('propria')
        self.campaign('de-outro', client='c3')
        self.db.commit()
        response = self.http.get('/clients/overview')
        self.assertEqual(response.status_code, 200)
        rows = {row['client_id']: row for row in response.json()}
        self.assertEqual(rows['c1']['campaign_count'], 1)
        self.assertNotIn('c3', rows)

    def test_report_selection_preserves_only_chosen_campaigns_and_metrics(self):
        first = self.campaign('chosen')
        first.report_metrics = {'spend': 100, 'clicks': 10, 'impressions': 100}
        other = self.campaign('not-selected')
        self.db.commit()
        response = self.http.post('/reports/', json={'client_id':'c1', 'campaign_metrics':{first.id:['cpc']}})
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(len(result['snapshot']['campaigns']), 1)
        self.assertEqual(result['snapshot']['campaigns'][0]['metrics'], {'cpc': 10.0})
        self.assertNotIn('not-selected', result['rendered_html'])
        self.assertNotIn('Impressões</td>', result['rendered_html'])
        stored = self.http.get('/reports/' + result['id']).json()
        self.assertEqual(stored['snapshot']['campaigns'][0]['metrics'], {'cpc': 10.0})
        self.assertEqual(self.http.post('/reports/', json={'client_id':'c1', 'campaign_metrics':{other.id:['invalid']}}).status_code, 422)
        foreign = self.campaign('foreign', client='c3')
        self.assertEqual(self.http.post('/reports/', json={'client_id':'c1', 'campaign_metrics':{foreign.id:['spend']}}).status_code, 422)

    def test_metric_defaults_are_per_user(self):
        self.assertEqual(self.http.put('/reports/metric-defaults', json={'metrics':['spend','clicks']}).status_code, 200)
        self.assertEqual(self.http.get('/reports/metric-defaults').json()['metrics'], ['spend','clicks'])
        from app.main import app
        from app.utils.auth import get_current_user
        from app.models.user import User
        app.dependency_overrides[get_current_user] = lambda: self.db.query(User).filter_by(id='u2').one()
        self.assertIsNone(self.http.get('/reports/metric-defaults').json()['metrics'])

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
