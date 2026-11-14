#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
docker info >/dev/null 2>&1 || { echo 'Docker Engine chưa chạy.' >&2; exit 1; }
test -f .env || { echo 'Chạy bash scripts/bootstrap.sh trước.' >&2; exit 1; }
docker compose up -d --build
docker compose ps
echo 'Kiểm tra URL APP_PUBLIC_URL trong .env; mặc định http://localhost:8080/admin'
echo 'Tài khoản local: .local/provisioned-admins.json. Không xóa volume để khởi động lại.'
