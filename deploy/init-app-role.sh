#!/bin/sh
# Runs ONLY when creating a fresh Postgres volume. Never rotates an existing role.
set -eu
APP_DB_PASSWORD=$(tr -d '\r\n' < /run/secrets/app_db_password)
export APP_DB_PASSWORD
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<'SQL'
\getenv app_password APP_DB_PASSWORD
SELECT format('CREATE ROLE dashflow_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', :'app_password') \gexec
GRANT CONNECT ON DATABASE dashflow TO dashflow_app;
GRANT USAGE, CREATE ON SCHEMA public TO dashflow_app;
SQL
unset APP_DB_PASSWORD
