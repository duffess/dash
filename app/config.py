from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "DashFlow"

    database_url: str


    #jwt
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080

    gemini_api_key: str = ""
    openai_api_key: str = ""

    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_developer_token: str = ""
    google_ads_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    frontend_base_url: str = "http://localhost:3000"

    meta_app_id: str = ""
    meta_app_secret: str = ""
    token_encryption_key: str = ""

    # Variaveis extras do .env
    google_ads_api_version: str = "v17"
    google_ads_refresh_token: str = ""

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

@lru_cache
def get_settings():
    # Carrega configs recarregadas do .env (Meta Ads Atualizado)
    return Settings()
