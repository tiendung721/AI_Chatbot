# Bảo mật và khoảng trống hiện tại — v2

Rà soát tài liệu/source ngày 13/11/2026, chưa chạy security test mới. Đọc master spec v2 mục 09/12 và checklist AT trước khi kết luận.

## Đã có code và bằng chứng local lịch sử

Tenant context server-side, PostgreSQL runtime RLS/default-deny và composite FK; strict DTO, CSRF/Origin Admin, Argon2id, Redis login rate, HttpOnly/SameSite cookie, session expiry/revoke/password change. Preview gắn phiên Admin.

Nguồn lọc version/tenant/release/scan/approval/hiệu lực/revoke; backend cấp evidence/locator. Sau generate kiểm lại nguồn; result/source/SSE cũ bị chặn khi nguồn thu hồi. React render text; không chạy script tài liệu.

M2 có private storage, ClamAV fail closed, parser/OCR tách mạng/secrets với giới hạn CPU/RAM/time và review. Purge live xóa dữ liệu dẫn xuất. TEST_REPORT ngày 10/11/2026 ghi coverage fixture, không thay security scan/corpus production.

API/worker không có migration URL. Không xuất raw provider errors/model/secrets ra client. .env/.local/trace/credentials không đưa vào Git hoặc log công khai.

## Khoảng trống v2 cần giải quyết

- MFA/recovery/session management Admin và kiểm thử chặt cho production.
- Domain allowlist/CSP trên HTML embed khác origin, Admin frame-ancestors none, trust proxy/postMessage/CORS đúng ranh giới.
- Prompt injection/live groundedness/PII minimization, source permissions và data-flow/provider retention được duyệt.
- Atomic budget/reserve/reconcile/unknown, concurrency/rate/session/tenant/global.
- Upload request-id/hard-kill/race, orphan/retention jobs, backup deletion/restore.
- Security/dependency/container scan, load/soak và production guards/deploy theo cấu hình thật.

OIDC công dân, Action confirmation/reconciliation, crawler SSRF và sandbox code/MCP không thuộc scope v2. Nếu làm công cụ tải corpus riêng, nó vẫn phải có allowlist/timeout/size/redirect kiểm soát; không biến source_url thành endpoint fetch tùy ý.

Production hiện bị chặn vô điều kiện ở Settings. Chỉ thay bằng validation production sau khi G4 có bằng chứng; không bỏ khóa để đưa local lên internet. MinIO/source/license/CVE/maintenance phải review trước chọn storage production; báo cáo lịch sử không tự chứng minh phù hợp production.

Không tuyên bố an toàn tuyệt đối/tuân thủ pháp luật chỉ vì tests pass. Go-live v2 dùng G0–G5, không cần IdP/API hồ sơ nhưng cần policy/nguồn/domain/UAT đúng phạm vi.
