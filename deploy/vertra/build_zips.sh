#!/usr/bin/env bash
# Gera dist/vertra/dash-api.zip e dist/vertra/dash-web.zip a partir da raiz do repositório.
# Uso: API_URL=https://dashflow-api.vertraweb.app bash deploy/vertra/build_zips.sh
set -euo pipefail
API_URL="${API_URL:-https://dashflow-api.vertraweb.app}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/dist/vertra"; TMP="$(mktemp -d)"
rm -rf "$OUT"; mkdir -p "$OUT" "$TMP/api" "$TMP/web"

cp -r "$ROOT/app" "$ROOT/alembic" "$ROOT/alembic.ini" "$TMP/api/"
cp "$ROOT/app/requirements.txt" "$TMP/api/requirements.txt"
cp "$ROOT/deploy/vertra/start_api.py" "$TMP/api/"
cp "$ROOT/deploy/vertra/api.vertracloud.config" "$TMP/api/vertracloud.config"
find "$TMP/api" -name __pycache__ -prune -exec rm -rf {} +
(cd "$TMP/api" && zip -qr "$OUT/dash-api.zip" .)

(cd "$ROOT/my-app" && VITE_API_BASE_URL="$API_URL" npx vite build --outDir "$TMP/web/dist" --emptyOutDir)
cp "$ROOT/my-app/server.mjs" "$TMP/web/"
cp "$ROOT/deploy/vertra/web.package.json" "$TMP/web/package.json"
cp "$ROOT/deploy/vertra/web.vertracloud.config" "$TMP/web/vertracloud.config"
(cd "$TMP/web" && zip -qr "$OUT/dash-web.zip" .)
rm -rf "$TMP"; ls -lh "$OUT"
