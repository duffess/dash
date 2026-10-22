from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.database import get_db
from app.config import get_settings
from app.models.client import Client
from app.models.integration import ClientIntegration
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.meta_ads import MetaAdsService
from app.utils.crypto import encrypt_text
from app.utils.oauth_state import issue_oauth_attempt, consume_oauth_attempt, finish_oauth

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/connect")
def connect_meta(
    response: Response,
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inicia o fluxo OAuth com o Facebook"""
    settings = get_settings()
    
    if not settings.meta_app_id or not settings.meta_app_secret:
        raise HTTPException(status_code=400, detail="Meta App credentials nao configuradas")

    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.user_id == current_user.id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    service = MetaAdsService(
        app_id=settings.meta_app_id,
        app_secret=settings.meta_app_secret,
        redirect_uri=settings.meta_redirect_uri,
    )

    auth_url = service.get_auth_url(
        state=issue_oauth_attempt(db, response, current_user.id, client.id, "meta_ads", settings)
    )
    return {"auth_url": auth_url}

@router.get("/callback")
def meta_auth_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """Recebe o callback do Facebook"""
    settings = get_settings()
    frontend_url = settings.frontend_base_url
    attempt = consume_oauth_attempt(db, request, state, "meta_ads", settings)

    if error or not code or not state:
        logger.warning("Meta OAuth não concluído ou callback incompleto.")
        return finish_oauth(RedirectResponse(url=f"{frontend_url}/clients?error=meta_auth_failed"), "meta_ads", settings)

    client_id = attempt["client_id"]
    user_id = attempt["user_id"]
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.user_id == user_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    integration = db.query(ClientIntegration).filter(
        ClientIntegration.client_id == client_id,
        ClientIntegration.platform == "meta_ads"
    ).first()

    service = MetaAdsService(
        app_id=settings.meta_app_id,
        app_secret=settings.meta_app_secret,
        redirect_uri=settings.meta_redirect_uri,
    )

    try:
        # Troca code por access token (long lived)
        token = service.exchange_code_for_token(code)
        
        if not integration:
            integration = ClientIntegration(
                client_id=client_id,
                platform="meta_ads",
                status="pending_account_select",
                access_token_encrypted=encrypt_text(token),
                refresh_token_encrypted=encrypt_text(token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=60)
            )
            db.add(integration)
        else:
            # Atualiza o token existente
            integration.access_token_encrypted = encrypt_text(token)
            integration.refresh_token_encrypted = encrypt_text(token) 
            integration.status = "pending_account_select"
            integration.expires_at = datetime.now(timezone.utc) + timedelta(days=60) 
            
        integration.sync_error = None
        db.commit()

        return finish_oauth(RedirectResponse(url=f"{frontend_url}/clients/{client_id}?status=pending_account_select&integration_id={integration.id}"), "meta_ads", settings)

    except Exception:
        logger.error("Falha ao processar callback Meta. Reconecte a conta e revise a configuração OAuth.")
        if integration:
            integration.status = "error"
            integration.sync_error = "Falha na autenticação Meta. Reconecte a conta e revise a configuração OAuth."
            db.commit()
        return finish_oauth(RedirectResponse(url=f"{frontend_url}/clients/{client_id}?error=meta_auth_process_failed"), "meta_ads", settings)
