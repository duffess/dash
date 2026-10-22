"""Real password/JWT/FastAPI regression tests using only dummy users."""
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
import test_campaign_sync as fixtures
from app.main import app
from app.models.user import User
from app.utils.auth import get_current_user, verify_password
from app.config import get_settings


class AuthenticationFlowTests(unittest.TestCase):
    def setUp(self):
        fixtures.CampaignFlowTests.setUp(self)
        app.dependency_overrides.pop(get_current_user)
        self.email='offline-auth@example.com'
        self.password='dummy-password-for-offline-tests-2026'

    def tearDown(self):
        fixtures.CampaignFlowTests.tearDown(self)

    def register(self):
        output=io.StringIO()
        with redirect_stdout(output):
            response=self.http.post('/auth/register',json={'email':self.email,'name':'Offline User','password':self.password})
        self.assertEqual(response.status_code,201,response.text)
        self.assertNotIn(self.password,output.getvalue())
        self.assertNotIn('password',response.json())
        self.assertNotIn('password_hash',response.json())
        user=self.db.query(User).filter_by(email=self.email).one()
        self.assertNotEqual(user.password_hash,self.password)
        self.assertTrue(verify_password(self.password,user.password_hash))
        return user

    def login(self):
        response=self.http.post('/auth/login',json={'email':self.email,'password':self.password})
        self.assertEqual(response.status_code,200,response.text)
        return {'Authorization':'Bearer '+response.json()['access_token']}

    def test_register_login_me_and_client_ownership(self):
        user=self.register()
        headers=self.login()
        me=self.http.get('/auth/me',headers=headers)
        self.assertEqual(me.status_code,200,me.text)
        self.assertEqual(me.json()['id'],user.id)
        self.assertEqual(self.http.get('/clients/',headers=headers).json(),[])
        self.assertEqual(self.http.get('/clients/c1',headers=headers).status_code,404)

    def test_wrong_password_and_missing_user_have_same_public_error(self):
        self.register()
        wrong=self.http.post('/auth/login',json={'email':self.email,'password':'dummy-wrong-password'})
        missing=self.http.post('/auth/login',json={'email':'missing-offline@example.com','password':'dummy-wrong-password'})
        self.assertEqual(wrong.status_code,401)
        self.assertEqual(missing.status_code,401)
        self.assertEqual(wrong.json(),missing.json())
        self.assertNotIn(self.password,wrong.text)

    def test_missing_tampered_and_previous_secret_tokens_are_rejected(self):
        self.register()
        headers=self.login()
        self.assertEqual(self.http.get('/auth/me').status_code,401)
        self.assertEqual(self.http.get('/auth/me',headers={'Authorization':'Bearer dummy-invalid-token'}).status_code,401)
        settings=get_settings()
        with patch.object(settings,'secret_key','different-dummy-jwt-secret-at-least-32-characters'):
            self.assertEqual(self.http.get('/auth/me',headers=headers).status_code,401)

    def test_validation_omits_rejected_input(self):
        response=self.http.post('/auth/register',json={'email':'not-an-email','password':123456})
        self.assertEqual(response.status_code,422)
        for error in response.json()['detail']:
            self.assertNotIn('input',error)
            self.assertNotIn('ctx',error)
