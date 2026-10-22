from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.client import Client
from app.models.integration import ClientIntegration
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.crypto import encrypt_text
from app.utils.oauth_state import issue_oauth_attempt, consume_oauth_attempt, finish_oauth

router = APIRouter()
settings = get_settings()


def _extract_customer_id(resource_name: str | None) -> str | None:
    if not resource_name:
        return None
    parts = resource_name.split("/")
    return parts[-1] if parts else None


def _fetch_google_account_id(refresh_token: str) -> str | None:
    if not settings.google_ads_client_id or not settings.google_ads_client_secret:
        return None

    from app.utils.google_ads import GoogleAdsService
    service = GoogleAdsService(
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
    )
    
    account_ids = service.list_accessible_customers(refresh_token)
    if not account_ids:
        return None

    # No MVP, pegamos a primeira conta disponível
    return account_ids[0]


@router.get("/connect")
def connect_google(
    response: Response,
    client_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inicia fluxo OAuth do Google para um cliente específico."""
    if not settings.google_ads_client_id or not settings.google_ads_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciais do Google Ads não configuradas no backend",
        )

    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.user_id == current_user.id)
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )

    state = issue_oauth_attempt(db, response, current_user.id, client_id, "google_ads", settings)
    params = {
        "client_id": settings.google_ads_client_id,
        "redirect_uri": settings.google_ads_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/adwords",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/callback")
def google_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Recebe callback do Google OAuth e persiste tokens da integração."""
    attempt = consume_oauth_attempt(db, request, state, "google_ads", settings)
    if error or not code:
        return finish_oauth(RedirectResponse(
            url=f"{settings.frontend_base_url}/clients?google_oauth=error&reason=authorization_failed",
            status_code=status.HTTP_302_FOUND,
        ), "google_ads", settings)

    user_id = attempt["user_id"]
    client_id = attempt["client_id"]

    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.user_id == user_id)
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado para callback",
        )

    try:
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "redirect_uri": settings.google_ads_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Erro ao obter token")

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resposta do Google sem access_token",
            )

        expires_at = None
        if isinstance(expires_in, int):
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        # REMOVED: Auto-selection of account_id
        # We now require the user to explicitly select their account from the frontend UI
        account_id = None

        existing = (
            db.query(ClientIntegration)
            .filter(
                ClientIntegration.client_id == client.id,
                ClientIntegration.platform == "google_ads",
            )
            .first()
        )

        if existing:
            existing.status = "pending_account_select"
            if account_id:
                existing.account_id = account_id
            existing.access_token_encrypted = encrypt_text(access_token)
            if refresh_token:
                existing.refresh_token_encrypted = encrypt_text(refresh_token)
            existing.expires_at = expires_at
            existing.sync_error = None
            integration_id = existing.id
        else:
            row = ClientIntegration(
                client_id=client.id,
                platform="google_ads",
                account_id=account_id,
                status="pending_account_select",
                access_token_encrypted=encrypt_text(access_token),
                refresh_token_encrypted=encrypt_text(refresh_token) if refresh_token else None,
                expires_at=expires_at,
                sync_error=None,
            )
            db.add(row)
            db.flush()
            integration_id = row.id

        db.commit()

        return finish_oauth(RedirectResponse(
            url=(
                f"{settings.frontend_base_url}/clients/{client.id}"
                f"?google_oauth=success&integration_id={integration_id}&status=pending_account_select"
            ),
            status_code=status.HTTP_302_FOUND,
        ), "google_ads", settings)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível concluir a conexão Google. Reconecte a conta e revise a configuração OAuth.",
        ) from None
