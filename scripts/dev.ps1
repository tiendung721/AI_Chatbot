$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $projectRoot
try {
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Engine chưa chạy. Mở Docker Desktop (Linux Engine) rồi thử lại.' }
    if (-not (Test-Path -LiteralPath '.env')) { throw 'Chạy .\scripts\bootstrap.ps1 trước.' }
    $portLine = Get-Content -LiteralPath '.env' | Where-Object { $_ -match '^APP_LOCAL_PORT=' } | Select-Object -First 1
    $localPort = if ($portLine) { [int]($portLine -split '=',2)[1] } else { 8080 }
    $runningServices = docker compose ps --status running --services
    if ($runningServices -notcontains 'nginx') {
        $listener = $null
        try { $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$localPort); $listener.Start() }
        catch { throw "Port $localPort đang được sử dụng. Đổi APP_LOCAL_PORT và APP_PUBLIC_URL trong .env; script không tự dừng process." }
        finally { if ($listener) { $listener.Stop() } }
    }
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) { throw 'Ứng dụng chưa khởi động thành công. Xem docker compose logs --tail 100.' }
    $ready = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        try { $health = Invoke-RestMethod -Uri "http://localhost:$localPort/health/ready" -TimeoutSec 3; if ($health.status -eq 'ready') { $ready=$true; break } } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw 'Ứng dụng chưa đạt readiness. Xem logs api/migrate/nginx.' }
    docker compose exec -T worker celery -A citizen_ai.workers:celery inspect ping --timeout 5
    if ($LASTEXITCODE -ne 0) { throw 'Worker chua san sang. Xem docker compose logs worker.' }
    $servicesNow = docker compose ps --status running --services
    if ($servicesNow -notcontains 'scheduler') { throw 'Scheduler chua chay. Xem docker compose logs scheduler.' }
    Write-Host "Đã sẵn sàng local: http://localhost:$localPort/admin"
    Write-Host 'Tài khoản: .local/provisioned-admins.json. Bắt buộc đổi mật khẩu lần đầu.'
    docker compose ps
} finally { Pop-Location }
