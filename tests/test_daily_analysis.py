"""Daily quota tests: no network or paid calls."""
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException
import test_campaign_sync as fixtures
from app.models.client import Client
from app.models.insight import Insight, DailyAnalysis
from app.utils.daily_analysis import daily_analysis


class DailyAnalysisTests(unittest.TestCase):
    setUp = fixtures.CampaignFlowTests.setUp
    tearDown = fixtures.CampaignFlowTests.tearDown
    campaign = fixtures.CampaignFlowTests.campaign

    def test_repeat_and_report_share_one_generation_and_snapshot(self):
        row = self.campaign('real')
        with patch('app.routers.insight.generate_analysis', return_value=('Analysis', 'test')) as ai:
            first = self.http.post('/insights/c1/generate').json()
            row.spend = 90
            self.db.commit()
            second = self.http.post('/insights/c1/generate').json()
            self.assertEqual(first['id'], second['id'])
            ai.assert_called_once()
        with patch('app.routers.report.generate_analysis') as ai:
            report = self.http.post('/reports/', json={'client_id': 'c1', 'include_ai': True})
            self.assertEqual(report.status_code, 201, report.text)
            self.assertEqual(report.json()['snapshot'], first['snapshot'])
            ai.assert_not_called()

    def test_failure_releases_quota_for_retry(self):
        self.campaign('real')
        with patch('app.routers.insight.generate_analysis', side_effect=HTTPException(503, 'Unavailable')):
            self.assertEqual(self.http.post('/insights/c1/generate').status_code, 503)
        self.assertEqual(self.db.query(DailyAnalysis).count(), 0)
        with patch('app.routers.insight.generate_analysis', return_value=('OK', 'test')):
            self.assertEqual(self.http.post('/insights/c1/generate').status_code, 201)

    def test_brasilia_midnight_and_independent_clients(self):
        self.campaign('real')
        self.campaign('other', 'c2')
        ai = Mock(return_value=('OK', 'test'))
        client = self.db.get(Client, 'c1')
        before = datetime(2026, 10, 22, 2, 59, tzinfo=timezone.utc)
        after = datetime(2026, 10, 22, 3, 0, tzinfo=timezone.utc)
        first = daily_analysis(self.db, client, ai, before)
        self.assertEqual(daily_analysis(self.db, client, ai, before).id, first.id)
        self.assertNotEqual(daily_analysis(self.db, client, ai, after).id, first.id)
        daily_analysis(self.db, self.db.get(Client, 'c2'), ai, after)
        self.assertEqual(ai.call_count, 3)

    def test_second_session_cannot_generate_while_provider_is_running(self):
        self.campaign('real')
        now = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
        second_ai = Mock()

        def provider(snapshot):
            with Session(self.engine) as other:
                with self.assertRaises(HTTPException) as error:
                    daily_analysis(other, other.get(Client, 'c1'), second_ai, now)
                self.assertEqual(error.exception.status_code, 409)
            return 'OK', 'test'

        daily_analysis(self.db, self.db.get(Client, 'c1'), provider, now)
        second_ai.assert_not_called()
        self.assertEqual(self.db.query(Insight).count(), 1)

    def test_report_first_then_brain_reuses_result(self):
        self.campaign('real')
        with patch('app.routers.report.generate_analysis', return_value=('Report AI', 'test')):
            self.assertEqual(self.http.post('/reports/', json={'client_id': 'c1', 'include_ai': True}).status_code, 201)
        with patch('app.routers.insight.generate_analysis') as ai:
            self.assertEqual(self.http.post('/insights/c1/generate').json()['content'], 'Report AI')
            ai.assert_not_called()
