"""Generate secrets for a NEW production installation. Never overwrites files."""
import argparse
import os
from pathlib import Path
import secrets
from cryptography.fernet import Fernet


def initialize(directory):
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Destination must be absent or empty. Existing installations require migration.")
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    password = secrets.token_urlsafe(36)
    values = {"postgres_password": secrets.token_urlsafe(36), "app_db_password": password,
              "database_url": f"postgresql+psycopg2://dashflow_app:{password}@db:5432/dashflow",
              "jwt_key": secrets.token_urlsafe(48), "token_key": Fernet.generate_key().decode(),
              "metrics_token": secrets.token_urlsafe(48), "backup_key": Fernet.generate_key().decode()}
    for name, value in values.items():
        descriptor = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(value + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(".secrets"))
    args = parser.parse_args()
    try:
        initialize(args.directory)
    except Exception:
        raise SystemExit("Segredos não foram inicializados. Use diretório privado vazio, sem substituir uma instalação existente.") from None
    print("Segredos gerados sem exibir valores. Proteja os arquivos e mantenha cópia offline da chave de backup.")
