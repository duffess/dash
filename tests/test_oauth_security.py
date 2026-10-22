"""Full FastAPI OAuth flow with fictitious providers and in-memory database."""
from contextlib import ExitStack
from datetime import datetime, timedelta
import hashlib
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import test_campaign_sync as fixtures
from app.config import get_settings
from app.main import app
from app.models.integration import ClientIntegration
from app.models.oauth_attempt import OAuthAttempt
from app.utils.crypto import decrypt_text


class OAuthSecurityFlowTests(unittest.TestCase):
    def setUp(self):
        fixtures.CampaignFlowTests.setUp(self)
        self.patches = ExitStack()
        settings = get_settings()
        for name,value in {'google_ads_client_id':'dummy-google-id', 'google_ads_client_secret':'dummy-google-secret',
                           'meta_app_id':'dummy-meta-id','meta_app_secret':'dummy-meta-secret'}.items():
            self.patches.enter_context(patch.object(settings,name,value))

    def tearDown(self):
        self.patches.close()
        fixtures.CampaignFlowTests.tearDown(self)

    def begin(self, provider):
        response=self.http.get(f'/auth/{provider}/connect',params={'client_id':'c1'})
        self.assertEqual(response.status_code,200,response.text)
        state=parse_qs(urlsplit(response.json()['auth_url']).query)['state'][0]
        platform='google_ads' if provider=='google' else 'meta_ads'
        cookie='dash_oauth_'+platform
        nonce=self.http.cookies.get(cookie)
        self.assertTrue(nonce)
        self.assertIn('HttpOnly',response.headers['set-cookie'])
        self.assertIn('SameSite=lax',response.headers['set-cookie'])
        self.assertEqual(response.headers['cache-control'],'no-store')
        return state,cookie,nonce

    def test_google_success_stores_encrypted_tokens_and_rejects_replay(self):
        state,cookie,nonce=self.begin('google')
        reply=Mock(status_code=200)
        reply.json.return_value={'access_token':'dummy-google-access','refresh_token':'dummy-google-refresh','expires_in':3600}
        with patch('app.routers.google_oauth.requests.post',return_value=reply) as provider:
            response=self.http.get('/auth/google/callback',params={'state':state,'code':'dummy-code'},follow_redirects=False)
            self.assertEqual(response.status_code,302,response.text)
            self.assertIn('google_oauth=success',response.headers['location'])
            row=self.db.query(ClientIntegration).filter_by(client_id='c1',platform='google_ads').one()
            self.assertEqual(decrypt_text(row.access_token_encrypted),'dummy-google-access')
            self.assertEqual(decrypt_text(row.refresh_token_encrypted),'dummy-google-refresh')
            self.assertEqual(row.status,'pending_account_select')
            self.assertIsNone(self.http.cookies.get(cookie))
            replay=self.http.get('/auth/google/callback',params={'state':state,'code':'dummy-code'},headers={'Cookie':f'{cookie}={nonce}'},follow_redirects=False)
            self.assertEqual(replay.status_code,400)
            provider.assert_called_once()

    def test_meta_success_and_replay(self):
        state,cookie,nonce=self.begin('meta')
        with patch('app.routers.meta_oauth.MetaAdsService.exchange_code_for_token',return_value='dummy-meta-access') as provider:
            response=self.http.get('/auth/meta/callback',params={'state':state,'code':'dummy-code'},follow_redirects=False)
            self.assertEqual(response.status_code,307,response.text)
            self.assertIn('status=pending_account_select',response.headers['location'])
            row=self.db.query(ClientIntegration).filter_by(client_id='c1',platform='meta_ads').one()
            self.assertEqual(decrypt_text(row.access_token_encrypted),'dummy-meta-access')
            replay=self.http.get('/auth/meta/callback',params={'state':state,'code':'dummy-code'},headers={'Cookie':f'{cookie}={nonce}'},follow_redirects=False)
            self.assertEqual(replay.status_code,400)
            provider.assert_called_once()

    def test_other_browser_is_rejected_before_provider_without_consuming_state(self):
        state,_,_=self.begin('google')
        with TestClient(app) as other, patch('app.routers.google_oauth.requests.post') as provider:
            response=other.get('/auth/google/callback',params={'state':state,'code':'dummy-code'},follow_redirects=False)
            self.assertEqual(response.status_code,400)
            provider.assert_not_called()
        attempt=self.db.get(OAuthAttempt,hashlib.sha256(state.encode()).hexdigest())
        self.assertIsNone(attempt.consumed_at)

    def test_expired_state_is_rejected_before_provider(self):
        state,_,_=self.begin('google')
        attempt=self.db.get(OAuthAttempt,hashlib.sha256(state.encode()).hexdigest())
        attempt.expires_at=datetime.utcnow()-timedelta(seconds=1)
        self.db.commit()
        with patch('app.routers.google_oauth.requests.post') as provider:
            response=self.http.get('/auth/google/callback',params={'state':state,'code':'dummy-code'},follow_redirects=False)
            self.assertEqual(response.status_code,400)
            provider.assert_not_called()

    def test_denied_consent_consumes_state_and_clears_cookie(self):
        for provider in ['google','meta']:
            state,cookie,nonce=self.begin(provider)
            with patch('app.routers.google_oauth.requests.post') as google, patch('app.routers.meta_oauth.MetaAdsService.exchange_code_for_token') as meta:
                response=self.http.get(f'/auth/{provider}/callback',params={'state':state,'error':'access_denied'},follow_redirects=False)
                self.assertIn(response.status_code,[302,307])
                self.assertIsNone(self.http.cookies.get(cookie))
                retry=self.http.get(f'/auth/{provider}/callback',params={'state':state,'code':'dummy-code'},headers={'Cookie':f'{cookie}={nonce}'},follow_redirects=False)
                self.assertEqual(retry.status_code,400)
                google.assert_not_called()
                meta.assert_not_called()

    def test_connect_rejects_other_users_client_without_issuing_state(self):
        for provider in ['google','meta']:
            response=self.http.get(f'/auth/{provider}/connect',params={'client_id':'c3'})
            self.assertEqual(response.status_code,404)
            self.assertNotIn('set-cookie',response.headers)
        self.assertEqual(self.db.query(OAuthAttempt).count(),0)
