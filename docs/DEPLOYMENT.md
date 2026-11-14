# Triển khai — hiện trạng local và phương án v2

Cập nhật tài liệu 13/11/2026, chưa triển khai hoặc tạo tài nguyên mới. Phạm vi: hỏi đáp công khai đa phường/xã, widget iframe khác origin; không citizen auth/Actions/API hồ sơ.

## Local hiện có

Compose có web, api, worker, scheduler, ingester, parser/OCR, ClamAV, PostgreSQL/pgvector, Redis, MinIO, Nginx và one-shot migrate. API/worker/parser không dùng migration credential; parser mạng internal/filesystem read-only/tmpfs và limits. Gateway chỉ bind localhost.

Scripts bootstrap/dev/check Windows/Linux giữ dữ liệu/.env/accounts; không reset volumes hoặc tự dừng process khác. Docker Linux containers đã có report local lịch sử, Linux host scripts chưa nghiệm thu độc lập. APP_ENV=production hiện bị chặn; chưa có production override được nghiệm thu.

## Phương án production

Single-host Linux Docker là baseline ban đầu, không tự có HA. Một origin HTTPS cho web/API/source/chatbot; các cổng nhúng iframe/loader từ origin này. Domain per tenant quản lý qua CLI/exact-origin allowlist/CSP; không dùng IdP/SSO hoặc database của cổng.

| Bước | Việc làm | Điều kiện kiểm tra |
|---|---|---|
| 1 | Xác nhận host/network/storage/backup/đội vận hành và data flow | Không tự mua/tạo tài nguyên; policy provider/retention rõ |
| 2 | Build locked images non-root, bỏ dev server/source mounts; review storage/dependencies | Security scan, license/CVE, manifest nonsecret |
| 3 | Cấp secrets production riêng, runtime DB role/RLS, MFA, pricing/budget và rate | Không demo credentials/Mock/default secrets; guards có test |
| 4 | Backup hiện trạng, migrate one-shot và kiểm compatibility | Không drop/reset volume; rollback ứng dụng có phương án |
| 5 | DNS/TLS/firewall/trust proxy/CSP/allowlist/health/metrics | Internal services không public; HTML embed đúng headers tenant |
| 6 | Đo load/soak và restore từ backup sang môi trường cách ly | Báo hardware/p95/queue/errors, RPO24h/RTO4h theo spec |
| 7 | Corpus/evaluation/live AI/domain thật và widget trên cổng | G2/G3/G4 và AT-44 có bằng chứng |
| 8 | Pilot 1–2 tenant, theo dõi 7 ngày baseline rồi bàn giao | G5/UAT, alert owner/runbooks/backup/retention rõ |

Có thể dùng VPS/cloud trong nước, cloud khác hoặc hạ tầng đơn vị sau khi duyệt. Dùng server trong nước không làm request AI bên ngoài thành xử lý nội địa. Không lựa chọn vendor/hardware trả phí khi chưa có đầu vào.

## Giới hạn và gates

Production code hiện chưa cho chạy. P4 mới thực hiện thay khóa vô điều kiện bằng guards đã kiểm chứng; yêu cầu thiếu MFA/budget/secret/RLS/TLS/policy vẫn phải chặn. Go-live G0–G5 trong master spec thay yêu cầu đủ M0–M8 v1.

Các ngưỡng tải/retention/restore là mục tiêu lập kế hoạch, chưa là SLA. Hạ tầng chưa chọn thì report local không được gọi là nghiệm thu production. Website sync/crawler/Actions/IdP không còn là điều kiện triển khai v2.
