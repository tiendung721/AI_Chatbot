$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $projectRoot
try {
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Engine chưa chạy.' }
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose config thất bại.' }
    docker compose build api tests
    if ($LASTEXITCODE -ne 0) { throw 'Build test image thất bại.' }
    docker compose run --rm --no-deps ops python -c "from citizen_ai.config import settings; c=settings(); assert c.app_env in {'local','test'} and c.ai_provider=='mock' and c.embedding_provider=='disabled', 'Checks require local Mock AI and disabled embeddings'"
    if ($LASTEXITCODE -ne 0) { throw 'Checks require local Mock AI and disabled embeddings; no paid API calls are allowed in checks.' }
    docker compose up -d postgres redis minio clamav parser worker ingester
    if ($LASTEXITCODE -ne 0) { throw 'M2 local services are not ready.' }
    docker compose run --rm tests ruff check --no-cache src tests migrations
    if ($LASTEXITCODE -ne 0) { throw 'Ruff thất bại.' }
    docker compose run --rm tests mypy --cache-dir=/tmp/citizen-mypy src
    if ($LASTEXITCODE -ne 0) { throw 'Python typecheck thất bại.' }
    docker compose run --rm tests
    if ($LASTEXITCODE -ne 0) { throw 'Pytest thất bại.' }
    docker compose build web
    if ($LASTEXITCODE -ne 0) { throw 'Frontend typecheck/build thất bại.' }
    Write-Host 'Backend checks và frontend build đạt. Browser E2E: npx --yes pnpm@12.18.0 test:e2e (cần cài dependency/browser theo README).'
} finally { Pop-Location }
