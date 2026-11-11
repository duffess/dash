from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal
from pydantic import model_validator
import base64
import hashlib
from urllib.parse import urlsplit
from app.utils.runtime_secrets import load_secret_files

load_secret_files()

class Settings(BaseSettings):
    app_name: str = "DashFlow"
    app_env: Literal["development", "test", "production"] = "development"
    https_redirect_enabled: bool = True
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8501"]
    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    max_request_bytes: int = 262144
    rate_limit_enabled: bool = True
    auth_requests_per_minute: int = 10
    ai_requests_per_minute: int = 5
    api_requests_per_minute: int = 180
    ops_metrics_token: str = ""

    database_url: str


    #jwt
    secret_key: str
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = 10080

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Explicit operator opt-in. Static demo reports never need a provider key.
    demo_ai_enabled: bool = False

    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    frontend_base_url: str = "http://localhost:3000"

    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://localhost:8000/auth/meta/callback"
    token_encryption_key: str = ""
    token_encryption_previous_keys: str = ""

    # Variaveis extras do .env
    google_ads_refresh_token: str = ""

    @model_validator(mode="after")
    def production_guards(self):
        if min(self.max_request_bytes, self.auth_requests_per_minute,
               self.ai_requests_per_minute, self.api_requests_per_minute) <= 0:
            raise ValueError("Os limites de requisição devem ser positivos")
        if self.app_env == "production":
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY de produção deve ter pelo menos 32 caracteres aleatórios")
            try:
                independent = base64.urlsafe_b64decode(self.token_encryption_key.encode("ascii"))
            except (ValueError, UnicodeError):
                independent = b""
            if len(independent) != 32 or independent == hashlib.sha256(self.secret_key.encode()).digest():
                raise ValueError("Produção exige TOKEN_ENCRYPTION_KEY independente e válida")
            if not self.rate_limit_enabled or not self.cors_origins or not self.trusted_hosts:
                raise ValueError("Produção exige limites, CORS e hosts explícitos")
            if any("*" in host or host in {"localhost", "127.0.0.1", "testserver"} for host in self.trusted_hosts):
                raise ValueError("Defina somente hosts de produção")
            urls = [self.frontend_base_url, self.google_ads_redirect_uri, self.meta_redirect_uri, *self.cors_origins]
            if any(urlsplit(url).scheme != "https" or not urlsplit(url).hostname or
                   urlsplit(url).hostname in {"localhost", "127.0.0.1"} for url in urls):
                raise ValueError("URLs públicas de produção devem usar HTTPS")
        return self

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "hide_input_in_errors": True,
    }

@lru_cache
def get_settings():
    # Carrega configs recarregadas do .env (Meta Ads Atualizado)
    return Settings()
