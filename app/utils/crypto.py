import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


def _derive_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache
def get_fernet() -> Fernet:
    settings = get_settings()
    raw_key = settings.token_encryption_key.strip()
    if raw_key:
        key_bytes = raw_key.encode("utf-8")
    else:
        # Fallback for local dev. In production set TOKEN_ENCRYPTION_KEY in .env.
        key_bytes = _derive_key_from_secret(settings.secret_key)
    return Fernet(key_bytes)


def encrypt_text(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")

