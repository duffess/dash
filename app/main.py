from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, campaign, client, google_oauth, meta_oauth, integration

app = FastAPI(
    title="DashFlow API",
    description="API para relatórios automatizados de marketing",
    version="0.1.0"
)

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit
        "http://localhost:3000",  # React
        "http://localhost:5173",  # Vite
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

# Importar routers
from app.routers import auth, campaign, client, integration

# Incluir routers
app.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
app.include_router(client.router, prefix="/clients", tags=["Clientes"])
app.include_router(campaign.router, prefix="/campaigns", tags=["Campanhas (Mock)"])
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
