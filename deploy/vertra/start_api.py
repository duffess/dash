"""Inicialização da API na Vertra Cloud: aplica as migrações e sobe o Uvicorn na porta da plataforma."""
import os
import subprocess
import sys

port = os.environ.get("PORT", "80")
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
# A plataforma termina o TLS e encaminha pelo proxy dela; o contêiner não é exposto diretamente.
os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port,
                           "--workers", "1", "--proxy-headers", "--forwarded-allow-ips",
                           os.environ.get("FORWARDED_ALLOW_IPS", "*"), "--no-access-log",
                           "--limit-concurrency", "100", "--timeout-keep-alive", "5"])
