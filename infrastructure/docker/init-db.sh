#!/bin/sh
set -eu
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=runtime_password="$APP_DATABASE_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE citizen_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD %L', :'runtime_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='citizen_runtime') \gexec
SQL
