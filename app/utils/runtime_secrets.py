"""Load Docker/host secret files before constructing settings, without logging."""
import os
from pathlib import Path

SECRET_NAMES = ("DATABASE_URL", "SECRET_KEY", "TOKEN_ENCRYPTION_KEY", "TOKEN_ENCRYPTION_PREVIOUS_KEYS",
                "GOOGLE_ADS_CLIENT_SECRET", "META_APP_SECRET", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPS_METRICS_TOKEN")


def load_secret_files():
    for name in SECRET_NAMES:
        filename = os.environ.get(name + "_FILE")
        if not filename:
            continue
        path = Path(filename)
        if not path.is_absolute() or not path.is_file() or path.stat().st_size > 8192:
            raise RuntimeError("Arquivo de segredo ausente, inválido ou excessivamente grande")
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise RuntimeError("Arquivo de segredo vazio")
        os.environ[name] = value
