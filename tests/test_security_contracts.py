"""Dependency-free contracts, also runnable in the isolated source sandbox.

Only named function/class definitions are loaded from the real source. Imports,
route decorators and default dependency expressions are NOT executed. Framework,
database and provider boundaries are doubles. These are unit contracts, not
end-to-end tests of FastAPI, SQLAlchemy, JSX or the providers' SDKs.
"""
import ast
import contextlib
import io
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
MARKER = "dummy-secret-never-log"


class HTTPError(Exception):
    def __init__(self, status_code, detail, **kwargs):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


def definitions(path, names, **bindings):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8-sig"))
    nodes = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in names]
    if {node.name for node in nodes} != set(names):
        raise AssertionError("Definition missing in " + path)
    for node in nodes:
        node.decorator_list = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.args.defaults = [value if isinstance(value, ast.Constant) else ast.Constant(None) for value in node.args.defaults]
            node.args.kw_defaults = [value if value is None or isinstance(value, ast.Constant) else ast.Constant(None)
                                     for value in node.args.kw_defaults]
    tree = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *nodes], type_ignores=[])
    namespace = {"HTTPException": HTTPError, **bindings}
    exec(compile(ast.fix_missing_locations(tree), str(ROOT / path), "exec"), namespace)
    return SimpleNamespace(**namespace)


class SecurityContracts(unittest.TestCase):
    def test_password_hash_does_not_print_password(self):
        context = Mock()
        context.hash.return_value = "dummy-hash"
        target = definitions("app/utils/auth.py", ["get_password_hash"], pwd_context=context)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(target.get_password_hash(MARKER), "dummy-hash")
        self.assertEqual(output.getvalue(), "")
        context.hash.assert_called_once_with(MARKER)

    def test_register_uses_hash_without_logging_payload(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        model = Mock()
        model.email = "dummy-column"
        target = definitions("app/routers/auth.py", ["register"], User=model,
                             get_password_hash=Mock(return_value="dummy-hash"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            target.register(SimpleNamespace(email="one@example.test", name="Dummy", password=MARKER), db)
        self.assertEqual(output.getvalue(), "")
        model.assert_called_once_with(email="one@example.test", name="Dummy", password_hash="dummy-hash")

    def test_frontend_auth_and_dashboard_do_not_log_payloads(self):
        auth = (ROOT / "my-app/src/contexts/AuthContext.jsx").read_text(encoding="utf-8-sig")
        self.assertNotIn("console.", auth)
        dashboard = (ROOT / "my-app/src/pages/Dashboard.jsx").read_text(encoding="utf-8-sig")
        self.assertNotIn("console.error('Erro ao buscar métricas:', error)", dashboard)

    def test_oauth_access_log_hides_all_callback_query_values(self):
        target = definitions("app/utils/safe_logging.py", ["OAuthAccessLogFilter"], logging=logging)
        for provider in ("google", "meta"):
            for suffix in ("", "/"):
                record = logging.LogRecord("uvicorn.access", 20, "dummy", 1, '%s - "%s %s HTTP/%s" %d',
                                           ("client", "GET", f"/auth/{provider}/callback{suffix}?code={MARKER}&state={MARKER}", "1.1", 302), None)
                self.assertTrue(target.OAuthAccessLogFilter().filter(record))
                self.assertNotIn(MARKER, record.getMessage())
                self.assertIn(f"/auth/{provider}/callback", record.getMessage())

    def test_other_access_log_records_are_preserved(self):
        target = definitions("app/utils/safe_logging.py", ["OAuthAccessLogFilter"], logging=logging)
        record = logging.LogRecord("uvicorn.access", 20, "dummy", 1, "%s", ("ordinary log",), None)
        target.OAuthAccessLogFilter().filter(record)
        self.assertEqual(record.getMessage(), "ordinary log")

    def test_filter_install_is_idempotent(self):
        logger = logging.Logger("dummy")
        target = definitions("app/utils/safe_logging.py", ["OAuthAccessLogFilter", "configure_access_logging"],
                             logging=SimpleNamespace(Filter=logging.Filter, getLogger=lambda name: logger))
        target.configure_access_logging()
        target.configure_access_logging()
        self.assertEqual(len(logger.filters), 1)
        main = (ROOT / "app/main.py").read_text(encoding="utf-8-sig")
        self.assertIn("configure_access_logging()", main)

    def test_validation_response_omits_input_and_context(self):
        target = definitions("app/main.py", ["safe_validation_error"],
                             JSONResponse=lambda **kwargs: kwargs, jsonable_encoder=lambda value: value)
        error = SimpleNamespace(errors=lambda: [{"loc": ["body", "password"], "msg": "Input should be a valid string",
                                               "type": "string_type", "input": {"token": MARKER}, "ctx": {"error": MARKER}}])
        # This handler has no await points. Drive it without opening asyncio's
        # socketpair, which the source-only sandbox intentionally forbids.
        with self.assertRaises(StopIteration) as completed:
            target.safe_validation_error(None, error).send(None)
        result = completed.exception.value
        self.assertEqual(result["status_code"], 422)
        self.assertNotIn(MARKER, str(result))
        self.assertEqual(set(result["content"]["detail"][0]), {"loc", "msg", "type"})

    def demo(self, enabled):
        ai = Mock(return_value=("dummy-analysis", "dummy-model"))
        snapshot = Mock(return_value={"source": "demo"})
        target = definitions("app/routers/report.py", ["demonstration_report"],
                             get_settings=lambda: SimpleNamespace(demo_ai_enabled=enabled),
                             demo_snapshot=snapshot, generate_analysis=ai, SimpleNamespace=SimpleNamespace,
                             SCENARIOS={"leads": "Leads"}, datetime=__import__("datetime").datetime,
                             timezone=__import__("datetime").timezone, report_response=lambda row: row)
        return target, ai, snapshot

    def test_paid_demo_is_disabled_by_default_configuration(self):
        tree = ast.parse((ROOT / "app/config.py").read_text(encoding="utf-8-sig"))
        settings = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Settings")
        field = next(node for node in settings.body if isinstance(node, ast.AnnAssign) and node.target.id == "demo_ai_enabled")
        self.assertIs(ast.literal_eval(field.value), False)

    def test_disabled_paid_demo_rejects_before_snapshot_or_provider(self):
        target, ai, snapshot = self.demo(False)
        with self.assertRaises(HTTPError) as error:
            target.demonstration_report(SimpleNamespace(include_ai=True, scenario="leads"), SimpleNamespace(id="dummy-user"))
        self.assertEqual(error.exception.status_code, 403)
        ai.assert_not_called()
        snapshot.assert_not_called()

    def test_static_demo_is_available_without_paid_ai(self):
        target, ai, _ = self.demo(False)
        row = target.demonstration_report(SimpleNamespace(include_ai=False, scenario="leads"), SimpleNamespace(id="dummy-user"))
        self.assertEqual(row.snapshot["source"], "demo")
        self.assertIsNone(row.analysis)
        ai.assert_not_called()

    def test_explicit_operator_opt_in_preserves_demo_feature(self):
        target, ai, _ = self.demo(True)
        row = target.demonstration_report(SimpleNamespace(include_ai=True, scenario="leads"), SimpleNamespace(id="dummy-user"))
        self.assertEqual(row.analysis, "dummy-analysis")
        ai.assert_called_once_with({"source": "demo"})

    def test_demo_status_requires_key_and_operator_flag(self):
        for key, enabled, expected in (("", True, False), ("dummy-key", False, False), ("dummy-key", True, True)):
            target = definitions("app/routers/insight.py", ["ai_status"],
                                 get_settings=lambda: SimpleNamespace(openai_api_key=key, openai_model="dummy", demo_ai_enabled=enabled))
            self.assertIs(target.ai_status(None)["demo_ai_enabled"], expected)

    def test_google_callback_masks_provider_exception(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id="dummy-client")
        settings = SimpleNamespace(frontend_base_url="http://example.test", google_ads_client_id="dummy-id",
                                   google_ads_client_secret=MARKER, google_ads_redirect_uri="http://example.test/callback")
        target = definitions("app/routers/google_oauth.py", ["google_callback"], settings=settings,
                             consume_oauth_attempt=lambda *args: {"user_id": "dummy-user", "client_id": "dummy-client"},
                             Client=SimpleNamespace(id="column", user_id="column"),
                             requests=SimpleNamespace(post=Mock(side_effect=RuntimeError(MARKER))),
                             status=SimpleNamespace(HTTP_500_INTERNAL_SERVER_ERROR=500))
        with self.assertRaises(HTTPError) as error:
            target.google_callback(None, "dummy-code", "dummy-state", None, db)
        self.assertEqual(error.exception.status_code, 500)
        self.assertNotIn(MARKER, error.exception.detail)
        self.assertTrue(error.exception.__suppress_context__)

    def test_meta_callback_does_not_log_or_store_provider_exception(self):
        integration = SimpleNamespace(status="connected", sync_error=None)
        db = Mock()
        db.query.return_value.filter.return_value.first.side_effect = [SimpleNamespace(id="dummy-client"), integration]
        service = Mock()
        service.exchange_code_for_token.side_effect = RuntimeError(MARKER)
        logger = Mock()
        target = definitions("app/routers/meta_oauth.py", ["meta_auth_callback"],
                             get_settings=lambda: SimpleNamespace(frontend_base_url="http://example.test", meta_app_id="dummy",
                                                                   meta_app_secret=MARKER, meta_redirect_uri="http://example.test/callback"),
                             consume_oauth_attempt=lambda *args: {"client_id": "dummy-client", "user_id": "dummy-user"},
                             Client=SimpleNamespace(id="column", user_id="column"),
                             ClientIntegration=SimpleNamespace(client_id="column", platform="column"),
                             MetaAdsService=Mock(return_value=service), logger=logger,
                             RedirectResponse=lambda **kwargs: kwargs, finish_oauth=lambda response, *args: response)
        result = target.meta_auth_callback(None, "dummy-code", "dummy-state", None, db)
        self.assertNotIn(MARKER, str(result))
        self.assertNotIn(MARKER, integration.sync_error)
        self.assertNotIn(MARKER, str(logger.mock_calls))
        self.assertEqual(integration.status, "error")

    def test_meta_token_exchange_masks_provider_body_and_error_chain(self):
        class RequestError(Exception):
            pass
        response = Mock(status_code=400)
        response.json.return_value = {"error": {"message": MARKER}}
        exception = RequestError(MARKER)
        exception.response = response
        request = Mock(side_effect=exception)
        target = definitions("app/utils/meta_ads.py", ["MetaAdsService"],
                             requests=SimpleNamespace(get=request, RequestException=RequestError))
        with self.assertRaises(RuntimeError) as error:
            target.MetaAdsService("dummy", MARKER, "http://example.test").exchange_code_for_token("dummy-code")
        self.assertNotIn(MARKER, str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)
        response.json.assert_not_called()

    def test_meta_long_lived_exchange_also_masks_error(self):
        class RequestError(Exception):
            pass
        response = Mock(status_code=400)
        exception = RequestError(MARKER)
        exception.response = response
        short = Mock()
        short.json.return_value = {"access_token": "dummy-short-token"}
        target = definitions("app/utils/meta_ads.py", ["MetaAdsService"],
                             requests=SimpleNamespace(get=Mock(side_effect=[short, exception]), RequestException=RequestError))
        with self.assertRaises(RuntimeError) as error:
            target.MetaAdsService("dummy", MARKER, "http://example.test").exchange_code_for_token("dummy-code")
        self.assertNotIn(MARKER, str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)

    def test_approved_python_snapshot_has_valid_syntax(self):
        # Parse only. Never import unreviewed application modules or resolve env.
        for folder in (ROOT / "app", ROOT / "tests"):
            for path in folder.rglob("*.py"):
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
