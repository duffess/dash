from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.database import get_db
from app.config import get_settings
from app.models.integration import ClientIntegration
from app.utils.meta_ads import MetaAdsService
from app.utils.crypto import encrypt_text

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/connect")
def connect_meta(client_id: str, db: Session = Depends(get_db)):
    """Inicia o fluxo OAuth com o Facebook"""
    settings = get_settings()
    
    if not settings.meta_app_id or not settings.meta_app_secret:
        raise HTTPException(status_code=500, detail="Meta App credentials nao configuradas")

    service = MetaAdsService(
        app_id=settings.meta_app_id,
        app_secret=settings.meta_app_secret,
        redirect_uri=f"{settings.frontend_base_url.replace(':3000', ':8000')}/auth/meta/callback"
    )

    # Passamos o proprio client_id como state parameter para recuperar no callback
    auth_url = service.get_auth_url(state=client_id)
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

    if error or not code or not state:
        logger.error(f"Erro no Meta OAuth: {error}")
        return RedirectResponse(url=f"{frontend_url}/clients?error=meta_auth_failed")

    client_id = state
    integration = db.query(ClientIntegration).filter(
        ClientIntegration.client_id == client_id,
        ClientIntegration.platform == "meta_ads"
    ).first()

    service = MetaAdsService(
        app_id=settings.meta_app_id,
        app_secret=settings.meta_app_secret,
        redirect_uri=f"{settings.frontend_base_url.replace(':3000', ':8000')}/auth/meta/callback"
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
