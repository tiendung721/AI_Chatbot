$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Cần cài Docker Desktop (Linux containers).' }
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Engine chưa chạy. Mở Docker Desktop, đợi Linux Engine sẵn sàng rồi chạy lại.' }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        python scripts/bootstrap_env.py
    } else {
        Write-Host 'Dùng image Python đã khóa phiên bản để sinh cấu hình local; không cài thêm công cụ trên máy.'
        docker run --rm --mount "type=bind,source=$projectRoot,target=/workspace" -w /workspace python:3.12.10-slim-bookworm python scripts/bootstrap_env.py
    }
    if ($LASTEXITCODE -ne 0) { throw 'Không tạo được cấu hình local.' }
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Cấu hình Compose chưa hợp lệ.' }
    docker compose build api minio
    if ($LASTEXITCODE -ne 0) { throw 'Build backend thất bại.' }
    docker compose up -d postgres redis minio migrate
    if ($LASTEXITCODE -ne 0) { throw 'Không khởi động được hạ tầng local.' }
    docker compose run --rm ops python -m citizen_ai.cli ops seed-demo
    if ($LASTEXITCODE -ne 0) { throw 'Chưa provision được dữ liệu mẫu. Xem logs migrate/postgres.' }
    docker compose run --rm ops python -m citizen_ai.cli ops init-storage
    if ($LASTEXITCODE -ne 0) { throw 'Object storage chưa sẵn sàng. Chạy lại bootstrap khi MinIO đã khởi động.' }
    Write-Host 'Bootstrap hoàn tất. Tài khoản local: .local/provisioned-admins.json (không đưa vào Git).'
    Write-Host 'Tiếp theo: .\scripts\dev.ps1'
} finally { Pop-Location }
