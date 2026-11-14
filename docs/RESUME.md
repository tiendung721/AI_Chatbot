# Điểm tiếp tục — P1 đã kiểm thử local, phạm vi v2

Cập nhật 13/11/2026. Người dùng đã cho code **W-01–W-09/P1**. Chưa có yêu cầu triển khai P2–P5, gọi AI tính phí hoặc public máy.

## Đọc trước

AGENTS.md, master spec v2, IMPLEMENTATION_STATUS, IMPLEMENTATION_PLAN, REQUIREMENTS_CHECKLIST, P1_IMPLEMENTATION_REPORT, TEST_REPORT và Git status/diff. Source phần lớn untracked; không reset/ghi đè.

## Đã làm

Migration 0004 metadata/approval/updated_at/supersedes và upload batches/receipts RLS. Metadata source/classification/tags/relations, request-id upload replay/concurrency/partial failures; file gốc private. Review ready/needs_review, immutable published, UI tìm/lọc/phân trang, chọn tri thức qua trang, version history/diff/text version. Purge redacts receipts và orphan sweeper CLI dry-run/grace/lock/ETag/DB/audit.

Corpus 22 file/22 hash/7 chủ đề ở fixtures/public_sources; bytes ở .local/public-corpus. Đã test 21 originals trích được, một HTML động EXTRACTION_EMPTY đúng dự kiến + ảnh scan dẫn xuất. Không publish hoặc gọi AI. Signed Office ZIP normalize trong memory, original giữ SHA; không xác minh chữ ký. PDF controls bị loại kèm warning. Preview provider ngoài chặn nguồn nội bộ/chưa approve trước khi gọi.

Generator scripts/update_requirement_checklist.py hiện là validator chỉ đọc, không còn sinh/hardcode pass theo 70 T-ID v1. Không dùng tool tự nâng trạng thái acceptance.

## Bằng chứng

Baseline 56 backend/6 Chromium. P1 backend source cuối 64 pass + 1 corpus skipped (42,14s); corpus riêng 1 pass (94,30s), Ruff/mypy29files/typecheck/generate-api/build đạt. Chromium bản cuối 8 pass (49,4s), gồm 6 regression + 2 luồng P1; readiness ready và worker/ingester đều pong sau khởi động lại stack. Test artifacts/credentials/trace chỉ trong .local hoặc report folders ignored.

Stack local API/worker/ingester/scheduler/web đã build/cập nhật; không đổi secrets/password người dùng, không xóa volume. Production vẫn khóa. .env/.local/trace có thể chứa secrets, không đưa vào Git/logs/report.

## Bước sau khi người dùng yêu cầu tiếp

W-10/P2: tách query embedding khỏi transaction rồi retrieval/quality/history/evaluation/preflight và Admin tối thiểu. Chưa semantic/live acceptance; key/model/pricing/budget/data policy/reviewer cần đúng bước, không tự bật embeddings/paid API.

P3: widget vẫn same-origin; chưa exact-origin/CSP khác origin. P4: chưa MFA, atomic budget/pricing, retention jobs/scheduler/checkpoint orphan toàn kho, load/security/restore. P5: domain/cổng thật/corpus nghiệp vụ/policy/UAT còn thiếu.

Giữ OUT ngoài scope: citizen auth/IdP/VNeID, hồ sơ cá nhân/Actions/phản ánh/đặt lịch, citizen attachments, live web/crawler/voice/image/code/MCP.

## Giới hạn quan trọng

allow_public_download là policy metadata, public source viewer hiện chỉ excerpt; UI không quảng bá tải original công khai. Hard-kill fixtures là process thật với lease expiry chủ động, chưa broker/host fault test. Orphan CLI tối đa10.000 objects/lần, dry-run mặc định, chưa sweeper scheduler/checkpoint toàn kho. Corpus technical không chứng minh đúng pháp lý/header/unit/layout/AI quality.

## Lệnh local

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
npx.cmd --yes pnpm@12.18.0 test:e2e
python scripts/update_requirement_checklist.py
~~~

check/E2E yêu cầu local/test + Mock + disabled embeddings; không tự chỉnh .env để test pass. Docker Desktop cần chạy, OCR/ClamAV đủ RAM. Cập nhật test report/status/resume bằng kết quả mới; không ghi M2/P1 là toàn bộ sản phẩm.
