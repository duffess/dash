import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet
import warnings

from app.config import get_settings


def _derive_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache
def get_fernet() -> MultiFernet:
    settings = get_settings()
    raw_key = settings.token_encryption_key.strip()
    if raw_key:
        key_bytes = raw_key.encode("utf-8")
    else:
        if settings.app_env == "production":
            raise RuntimeError("Configure uma chave independente antes de iniciar produção")
        warnings.warn("Cifra legada de desenvolvimento. Execute migrate_token_encryption antes de trocar SECRET_KEY.",
                      DeprecationWarning, stacklevel=2)
        key_bytes = _derive_key_from_secret(settings.secret_key)
    previous = [key.strip() for key in settings.token_encryption_previous_keys.split(",") if key.strip()]
    if len(previous) > 5:
        raise ValueError("Muitas chaves antigas de criptografia")
    return MultiFernet([Fernet(key_bytes), *(Fernet(key.encode("ascii")) for key in previous)])


def encrypt_text(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")

