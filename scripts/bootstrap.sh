#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
docker info >/dev/null 2>&1 || { echo 'Docker Engine chưa chạy.' >&2; exit 1; }
if command -v python3 >/dev/null 2>&1; then python3 scripts/bootstrap_env.py; else
  echo 'Dùng image Python đã khóa để sinh .env local.'
  docker run --rm --mount "type=bind,source=$(pwd),target=/workspace" -w /workspace python:3.12.10-slim-bookworm python scripts/bootstrap_env.py
fi
docker compose config --quiet
docker compose build api minio
docker compose up -d postgres redis minio migrate
docker compose run --rm ops python -m citizen_ai.cli ops seed-demo
docker compose run --rm ops python -m citizen_ai.cli ops init-storage
echo 'Bootstrap hoàn tất. Tài khoản local: .local/provisioned-admins.json. Tiếp: bash scripts/dev.sh'
