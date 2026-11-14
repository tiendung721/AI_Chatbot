# Chạy local và chuẩn bị triển khai

Compose hiện có web, api, worker, scheduler, ingester, parser/OCR, ClamAV, PostgreSQL/pgvector, Redis, MinIO, Nginx và one-shot migrate. `ops`/`tests` là profiles riêng. API/worker/scheduler/ingester/parser chạy non-root; không mount Docker socket hoặc nhận migration credential. Parser không có DB/AI secrets, chỉ network internal `parsing`, root filesystem read-only/tmpfs và CPU/RAM/PID limits. Chỉ gateway bind 127.0.0.1; dịch vụ còn lại không có host port.

`bootstrap.ps1`/`.sh` tạo secrets ngẫu nhiên khi chưa có `.env`, build image, migrate, seed hai phường mẫu, kiểm tra bucket riêng tư. `dev.ps1` kiểm tra Engine/port/readiness và worker/scheduler. Scripts không reset volume, không đổi ExecutionPolicy và không tự dừng process khác. Script PowerShell dùng UTF-8 BOM để tương thích Windows PowerShell 5.1.

Image có version/digest; source MinIO local có commit và checksum. Đây là môi trường phát triển local, không phải kiến trúc HA. `APP_ENV=production` hiện bị chặn có chủ đích; chưa có production override được nghiệm thu.

| Hạ tầng sau này | Công việc cần bổ sung | Điều cần xác nhận |
|---|---|---|
| VPS/cloud trong nước | DB/storage/backup/giám sát/TLS | Gọi OpenAI vẫn là luồng xử lý ngoài; phải duyệt data flow |
| Cloud quốc tế | Managed services/network/region/backup | Hợp đồng, residency, retention và dữ liệu được phép xử lý |
| Hạ tầng đơn vị | Server/network/patch/backup/nhân sự | Model API không cần GPU local; model nội bộ cần adapter/hạ tầng riêng |

Trước production: MFA, domain/TLS/reverse proxy trust, IdP/connector thật, scanning, data policy, budget controls, monitoring, restore drill, security review và UAT theo master spec. Không chỉ bỏ validator để đưa local lên internet. DNS/domain và cert chưa được tạo; không có cloud resources tính phí được cấp trong phiên này.
