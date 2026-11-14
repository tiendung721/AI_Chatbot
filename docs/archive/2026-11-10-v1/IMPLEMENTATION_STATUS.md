# Trạng thái triển khai — 10/11/2026

**M0–M1 và phần cốt lõi M2 đã chạy/kiểm thử local. Toàn bộ sản phẩm chưa hoàn thành; production bị chặn.** Không có live AI/UAT hoặc tích hợp hồ sơ công dân thật.

| Milestone | Status | Bằng chứng và giới hạn |
|---|---|---|
| M0 | implemented_and_tested | pnpm/uv locks, Docker, Alembic 0001/0002, runtime RLS, CLI, basic Admin auth, cấu hình fail closed; bootstrap/dev/check thực chạy |
| M1 | implemented_and_tested | UI → API → PostgreSQL/outbox → Celery → retrieval/Mock → kiểm tra nguồn → SSE/result/feedback; 33 backend tests + 4 Chromium E2E pass |
| M2 | in_progress | Upload/private storage/ClamAV thật, parser/OCR, review/metadata/versioning, source locator, purge và pgvector/hybrid đã có code và test local. Chưa live semantic benchmark, tài liệu nghiệp vụ/layout phức tạp và hard-crash/load/security/restore acceptance |
| M3 | not_started | Có builder/release tối thiểu M1; website sync, evaluation đầy đủ, trace và UI nâng cao chưa có |
| M4 | not_started | Chưa có OIDC/Actions; live dependency chưa được cấp |
| M5 | not_started | Chưa có adapters nâng cao/attachments/web/voice/image/code/MCP |
| M6 | not_started | Có usage token events unpriced cơ bản; chưa có pricing/quota reservation/dashboard/retention đầy đủ |
| M7 | not_started | Chưa MFA/security scan/load/restore/HA/production packaging |
| M8 | blocked_external_dependency | Chưa có key/model live, nguồn thật, IdP/API nghiệp vụ, data policy/domain/UAT |

## Yêu cầu sản phẩm

| Requirement | Status | Implementation / Tests / Limitations / Next action |
|---|---|---|
| REQ-01 | in_progress | DB RLS/composite FK và UI/API hai tenant đã test; mở rộng isolation cho các module M2–M6 sau khi triển khai |
| REQ-02 | in_progress | Anonymous chat đã E2E; chưa có citizen auth/ownership với API thật, tiếp M4 |
| REQ-03 | in_progress | Văn bản + file có version/chunks/scan/review/approval/release/thu hồi/purge thật; website sync M3 chưa triển khai |
| REQ-04 | in_progress | Registry trạng thái tối thiểu và chặn capability chưa cấp; adapters mở rộng còn thiếu |
| REQ-05 | in_progress | Một Admin active/tenant, CLI provision/rotate, phiên và đổi password; MFA/khôi phục hoàn chỉnh ở M7 |
| REQ-06 | not_started | Chưa ActionGateway/confirmation/idempotency upstream; tiếp M4 |
| REQ-07 | in_progress | Linux Docker images build/chạy thật trên Docker Desktop; chưa nghiệm thu Linux host scripts/production/HA |
| REQ-08 | in_progress | Có audit, dashboard đếm thực và usage events unpriced; quota/monitoring/backup còn thiếu |
| REQ-09 | in_progress | Nền tảng/lát cắt đầu tiên; chưa đủ go-live gates |
| REQ-10 | implemented_and_tested | `schemas.py`, `config.py`, `ai/adapters.py`, `main.py`, Admin UI; unit/integration model injection + browser API test pass. Model/provider/key không thuộc Admin DTO/UI |

## Capabilities

CAP-01: in_progress — lexical và pgvector exact cosine/RRF có tenant/profile/release/approval/effectivity/revocation đã test thật; embedding SDK contract test, chưa có semantic evaluation với AI và nguồn thật. Embeddings tắt mặc định.

CAP-02, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07, CAP-08, CAP-09: not_started — API trạng thái hiển thị `not_implemented/not_granted`, schema không cho bật. Không có output giả.

## Giao diện

| UI | Status | Phạm vi thực tế |
|---|---|---|
| UI-01 | in_progress | Login/đổi password/logout; MFA chưa có |
| UI-02 | in_progress | Counts/paused trạng thái thật; analytics nâng cao chưa có |
| UI-03 | implemented_and_tested | Tên/mô tả/Instructions/lời chào/starters + draft revision, không model selector |
| UI-04 | in_progress | Có upload batch/progress/version/retry/approval/revoke/purge; danh sách tối đa 200 phiên bản, filter/pagination còn thiếu |
| UI-05 | in_progress | Có extraction sections/locator/edits/review, sheet ẩn/cảnh báo, metadata cơ bản và file gốc sạch; chưa đầy đủ mọi metadata trong đặc tả |
| UI-06 | in_progress | Soạn text/Markdown canonical; chưa rich text editor |
| UI-07 | not_started | Website sources |
| UI-08 | in_progress | Backend capability status; chưa trang quản trị toggles đầy đủ |
| UI-09 | not_started | Actions |
| UI-10 | in_progress | Draft Preview với nguồn thật; chưa trace/evaluation đầy đủ |
| UI-11 | not_started | Evaluation UI |
| UI-12 | in_progress | Validate tối thiểu/publish/history/rollback đã test; regression/data quality gates nâng cao M3 |
| UI-13 | not_started | Admin hội thoại/redaction UI |
| UI-14 | not_started | Usage/quota dashboard |
| UI-15 | in_progress | Trang chat/widget iframe/copy code thủ công cùng nguồn; domain/branding đầy đủ chưa có |
| UI-16 | in_progress | Session/password nền tảng; chưa màn MFA/recovery/session management đầy đủ |

Test IDs T-01–T-70 được theo dõi riêng trong `REQUIREMENTS_CHECKLIST.md`. Lệnh/kết quả thực tế ở `TEST_REPORT.md`. Không diễn giải số test pass thành 70 acceptance scenarios đã hoàn tất.

Chat/embedding OpenAI adapters: tested ở mức contract giả lập SDK; **live_verified: chưa có**. Không gọi paid API trong phiên này. Chi tiết phần còn lại ở `RESUME.md`; không dùng số lượng test để tuyên bố full product.
