#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
docker info >/dev/null 2>&1 || { echo 'Docker Engine chưa chạy.' >&2; exit 1; }
docker compose config --quiet
docker compose build api tests
docker compose run --rm --no-deps ops python -c "from citizen_ai.config import settings; c=settings(); assert c.app_env in {'local','test'} and c.ai_provider=='mock' and c.embedding_provider=='disabled', 'Checks require local Mock AI and disabled embeddings'"
docker compose up -d postgres redis minio clamav parser worker ingester
docker compose run --rm tests ruff check --no-cache src tests migrations
docker compose run --rm tests mypy --cache-dir=/tmp/citizen-mypy src
docker compose run --rm tests
docker compose build web
echo 'Backend checks/frontend build đạt. Browser E2E chạy riêng theo README.'
