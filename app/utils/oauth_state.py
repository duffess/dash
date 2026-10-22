"""Opaque state + HttpOnly browser cookie + atomic database consumption."""
from datetime import datetime, timedelta
import hashlib
import re
import secrets
from fastapi import HTTPException
from sqlalchemy import text

TTL_SECONDS = 600


def _digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def cookie_name(platform, production=False):
    if platform not in {"google_ads", "meta_ads"}:
        raise ValueError("Unsupported OAuth platform")
    return ("__Host-" if production else "") + "dash_oauth_" + platform


def cookie_path(platform, production=False):
    if production:
        return "/"
    return "/auth/google" if platform == "google_ads" else "/auth/meta"


def issue_oauth_attempt(db, response, user_id, client_id, platform, settings):
    production = settings.app_env == "production"
    name = cookie_name(platform, production)
    state, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now = datetime.utcnow()
    db.execute(text("DELETE FROM oauth_attempts WHERE expires_at < :cutoff"),
               {"cutoff": now - timedelta(days=1)})
    db.execute(text("""INSERT INTO oauth_attempts
        (state_hash, browser_hash, user_id, client_id, platform, expires_at)
        VALUES (:state_hash, :browser_hash, :user_id, :client_id, :platform, :expires_at)"""),
        {"state_hash": _digest(state), "browser_hash": _digest(browser), "user_id": user_id,
         "client_id": client_id, "platform": platform, "expires_at": now + timedelta(seconds=TTL_SECONDS)})
    db.commit()
    response.set_cookie(name, browser, max_age=TTL_SECONDS, httponly=True, samesite="lax",
                        secure=production, path=cookie_path(platform, production))
    response.headers["Cache-Control"] = "no-store"
    return state


def consume_oauth_attempt(db, request, state, platform, settings=None):
    browser = request.cookies.get(cookie_name(platform, settings is not None and settings.app_env == "production"), "")
    if not all(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", value)
               for value in (state, browser)):
        raise HTTPException(status_code=400, detail="Conexão expirada ou iniciada em outro navegador. Inicie novamente.")
    now = datetime.utcnow()
    params = {"state_hash": _digest(state), "browser_hash": _digest(browser), "platform": platform, "now": now}
    row = db.execute(text("""SELECT user_id, client_id FROM oauth_attempts
        WHERE state_hash=:state_hash AND browser_hash=:browser_hash AND platform=:platform
          AND consumed_at IS NULL AND expires_at > :now"""), params).mappings().first()
    if not row:
        raise HTTPException(status_code=400, detail="Conexão inválida, expirada ou já utilizada. Inicie novamente.")
    updated = db.execute(text("""UPDATE oauth_attempts SET consumed_at=:now
        WHERE state_hash=:state_hash AND browser_hash=:browser_hash AND platform=:platform
          AND consumed_at IS NULL AND expires_at > :now"""), params)
    if updated.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Esta conexão já foi utilizada. Inicie novamente.")
    # Persist consumption BEFORE exchanging the provider code, across workers.
    db.commit()
    return dict(row)


def finish_oauth(response, platform, settings):
    production = settings.app_env == "production"
    response.delete_cookie(cookie_name(platform, production), path=cookie_path(platform, production), httponly=True,
                           secure=settings.app_env == "production", samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
