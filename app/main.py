from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.utils.safe_logging import configure_access_logging
from app.config import get_settings
from app.utils.security_http import RequestPolicy, SecurityHTTPMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi import Request, HTTPException
from sqlalchemy import text
import secrets
from app.routers import auth, campaign, client, google_oauth, meta_oauth, integration

configure_access_logging()
settings = get_settings()
request_policy = RequestPolicy(settings)

app = FastAPI(
    title="DashFlow API",
    description="API para relatórios automatizados de marketing",
    version="0.1.0",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    openapi_url=None if settings.app_env == "production" else "/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request, exc):
    # Pydantic v2 includes rejected input (possibly a password/token) by default.
    errors = [{key: error[key] for key in ("loc", "msg", "type") if key in error}
              for error in exc.errors()]
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": errors}))

app.add_middleware(SecurityHTTPMiddleware, settings=settings, policy=request_policy)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
if settings.app_env == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
# CORS wraps admission errors too, so the frontend can read 413/429 responses.
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", "Accept"], expose_headers=["X-Request-ID"])


@app.get("/")
def read_root():
    return {
        "message": "DashFlow API está rodando! 🚀",
        "version": "0.1.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/ready", include_in_schema=False)
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Serviço temporariamente indisponível.") from None
    return {"status": "ready"}


@app.get("/ops/metrics", include_in_schema=False)
def operations_metrics(request: Request):
    token = settings.ops_metrics_token
    if not token or not secrets.compare_digest(request.headers.get("authorization", "").encode(), ("Bearer " + token).encode()):
        raise HTTPException(status_code=404, detail="Não encontrado.")
    return request_policy.metrics()

# Importar routers
from app.routers import auth, campaign, client, integration

# Incluir routers
app.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
app.include_router(client.router, prefix="/clients", tags=["Clientes"])
app.include_router(campaign.router, prefix="/campaigns", tags=["Campanhas"])
app.include_router(integration.router, prefix="/integrations", tags=["Integracoes"])
from app.routers import insight
app.include_router(insight.router, prefix="/insights", tags=["Insights IA"])

# Criar tabelas no banco
from app.database import engine, Base
from app.models import campaign as campaign_model, client as client_model, integration as integration_model, user

@app.on_event("startup")
def startup_event():
    # Migrations will be handled by Alembic (production ready)
    pass

app.include_router(google_oauth.router, prefix="/auth/google", tags=["Google OAuth"])
app.include_router(meta_oauth.router, prefix="/auth/meta", tags=["Meta OAuth"])
from app.routers import report
app.include_router(report.router, prefix="/reports", tags=["Relatórios"])
