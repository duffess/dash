from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging
from jose import JWTError, jwt

from app.database import get_db
from app.config import get_settings
from app.models.client import Client
from app.models.integration import ClientIntegration
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.meta_ads import MetaAdsService
from app.utils.crypto import encrypt_text

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_state_token(user_id: str, client_id: str, settings) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "client_id": client_id,
            "platform": "meta_ads",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def _decode_state_token(state: str, settings) -> dict:
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State invalido ou expirado",
        ) from exc

    if (
        payload.get("platform") != "meta_ads"
        or not payload.get("sub")
        or not payload.get("client_id")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State invalido para Meta Ads",
        )
    return payload

@router.get("/connect")
def connect_meta(
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
        state=_build_state_token(current_user.id, client.id, settings)
    )
    return {"auth_url": auth_url}

@router.get("/callback")
def meta_auth_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """Recebe o callback do Facebook"""
    settings = get_settings()
    frontend_url = settings.frontend_base_url

    if error or not code or not state:
        logger.error(f"Erro no Meta OAuth: {error}")
        return RedirectResponse(url=f"{frontend_url}/clients?error=meta_auth_failed")

    state_payload = _decode_state_token(state, settings)
    client_id = state_payload["client_id"]
    user_id = state_payload["sub"]
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
                status="connected",
                access_token_encrypted=encrypt_text(token),
                refresh_token_encrypted=encrypt_text(token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=60)
            )
            db.add(integration)
        else:
            # Atualiza o token existente
            integration.access_token_encrypted = encrypt_text(token)
            integration.refresh_token_encrypted = encrypt_text(token) 
            integration.status = "connected"
            integration.expires_at = datetime.now(timezone.utc) + timedelta(days=60) 
            
        db.commit()

        return RedirectResponse(url=f"{frontend_url}/clients/{client_id}")

    except Exception as e:
        logger.error(f"Erro ao processar callback Meta: {str(e)}")
        if integration:
            integration.status = "error"
            integration.sync_error = str(e)
            db.commit()
        return RedirectResponse(url=f"{frontend_url}/clients/{client_id}?error=meta_auth_process_failed")
