# Báo cáo triển khai P1 — W-01 đến W-09

Ngày: 13/11/2026. Phạm vi: quản lý tri thức và vòng đời tài liệu local, theo đặc tả v2.
Kết luận: phần triển khai/kiểm thử P1 đã thực hiện; chưa phải hoàn thành sản phẩm hoặc go-live.

## Công việc và đầu ra

| Task | Kết quả thực hiện | Bằng chứng chính |
|---|---|---|
| W-01 | Generator v1 đổi thành validator FR/NFR/W/AT chỉ đọc, bỏ hardcoded test pass và không ghi đè checklist | python scripts/update_requirement_checklist.py đạt; archive T-ID giữ nguyên |
| W-02 | Khởi động Docker Desktop khi Engine chưa chạy; baseline trước sửa | check.ps1: 56 backend, 6 Chromium, lint/type/build đạt |
| W-03 | Catalog/manifest có provenance/hash/phạm vi/label cho 22 nguồn, 7 chủ đề và hai tenant fixture | fixtures/public_sources + EXTRACTION_REPORT |
| W-04 | Migration 0004, metadata/source/tags/classification/supersedes/approval audit, strict validation | test_p1 metadata/FK/RLS, test_policy, schema TypeScript sinh lại |
| W-05 | Batch manifest/fingerprint, unique operation receipts, replay/concurrency/partial reject; unknown commit không xóa object mù | test_batch_retry_concurrency_and_payload_conflict |
| W-06 | Public corpus qua private storage/ClamAV/parser; hỗ trợ ZIP Office đường dẫn Windows, warning chữ ký, normalize text controls | unit Office collision/control + opt-in corpus 1 pass |
| W-07 | Serialize review/metadata với publish, lease/fencing/retry, kill process thật sau parse và sau delete-object; revoke/purge giữa parse | test_hard_kill_parse_and_purge_then_recover và test_stale_parse_cannot_resurrect... |
| W-08 | Kho/history phân trang, search/filter, diff giới hạn, review ready, tạo text version; UI chọn qua trang và metadata/diff | API 205 versions/11 pages, browser p1.spec.ts |
| W-09 | Purge receipt redaction; orphan dry-run/apply theo tenant/grace/DB pointer/ETag/size và audit | test_orphan_sweep_grace_dry_run_and_tenant_boundary + purge/race tests |

## Những ranh giới giữ nguyên

Tenant server-side, runtime PostgreSQL RLS/force/no owner/BYPASSRLS, strict Admin DTO và Developer-only runtime. Không gọi paid API, không mở production/Internet, không đổi .env/password người dùng hoặc reset volumes/Git/push.

Tài liệu công khai được đưa vào tenant fixture và gắn internal/unapproved cho kiểm kỹ thuật; không publish vào kho người dùng. File gốc DOCX được đối chiếu SHA256 sau parse để bảo đảm bản chuẩn hóa chỉ ở trong parser.

## Kiểm chứng

- Full backend source hiện tại: 64 passed, 1 skipped trong 42,14 giây. Skipped là corpus opt-in, đã chạy riêng.
- Ruff src/tests/migrations đạt; mypy đạt 29 source files. Hai script corpus/checklist cũng qua Ruff.
- check.ps1 đạt build/backend/frontend; sau guard dữ liệu kiểm lại source bằng mounted test image và build API cuối.
- Corpus riêng cuối: 1 passed trong 94,30 giây; 22 file gốc + ảnh dẫn xuất, 508 trang PDF; 21 originals trích xuất, một HTML trống fail đúng dự kiến. Tổng thời gian từng case 88 giây.
- pnpm generate:api/typecheck đạt. Frontend production build cuối có TypeScript check đạt.
- Browser regression và hai luồng P1: 8 passed trong 49,4 giây, Chromium; artifact .local/evidence/p1-catalog.png và p1-version-diff.png. Lượt bị mất kết nối do stack dừng không được tính pass; đã chạy lại đủ sau khởi động stack.
- Migration 0004 đã chạy tiến, stack local cập nhật/readiness/worker ping đạt.

Không quy số backend tests thành số AT acceptance đã hoàn tất. Bằng chứng P1 chỉ đủ cho các phần local của các AT được ánh xạ, không thay live quality/production/UAT.

## Các lỗi phát hiện trong quá trình làm

1. Orphan cleanup so LastModified tuyệt đối giữa list/head không tương thích độ chính xác timestamp S3: dùng ETag/size và kiểm cutoff hiện tại trước xóa.
2. Signed DOCX ZIP Windows separators: preflight và parser normalize an toàn, reject collision/traversal, không xác minh chữ ký.
3. PDF tạo control chars PostgreSQL không nhận: sanitize + NFC + warning để review.
4. HTML nguồn động không có text: giữ EXTRACTION_EMPTY, không giả trích xuất thành công hoặc thêm crawler.
5. Form metadata remount theo revision làm mất thông báo lưu: chỉ remount khi đổi version.
6. Tests cũ giả định một status/không combobox và extraction chỉ đọc: đổi selector theo hành vi mới, vẫn kiểm model injection và CSRF. Request setup E2E P1 bổ sung Origin hợp lệ thay vì nới bảo vệ backend.
7. Đối chiếu metadata hiển thị JSON/UUID: UI thay bằng nhãn/value tiếng Việt; hash chuyển vào thông tin file tùy mở.
8. Phân loại internal/restricted phải có tác dụng với Preview AI: chặn nguồn chưa duyệt trước provider ngoài, test cấu hình giả lập không có paid request.

## Giới hạn để tiếp tục đúng phạm vi

P2 còn semantic/live evaluation, history có kiểm chứng, query embedding ngoài transaction và preflight/evaluation gắn hash đầy đủ. P3 nhúng khác origin chưa triển khai. P4 còn MFA/budget/pricing/retention định kỳ/load/security/restore/production. P5 chưa có UAT/domain/corpus nghiệp vụ được duyệt.

Policy allow_public_download đã lưu trong metadata; public hiện vẫn mở excerpt, chưa có UI tải original công khai. Orphan CLI là batch có giới hạn, chưa vòng quét tự động toàn kho hoặc backup deletion. Process crash tests có lease expiry chủ động, không phải nghiệm thu host/broker outage. Chuẩn hóa đường dẫn/đọc đủ trang không chứng nhận nội dung pháp lý, chữ ký hoặc mọi layout đúng.

## Dùng thử

Stack local đã chạy tại http://localhost:8080/admin. Dùng tài khoản hiện có; không công bố .local/provisioned-admins.json. Trong kho có thể tìm/lọc/page, xem nội dung/metadata, duyệt phần trích xuất, thêm version, so sánh và revoke/purge.

Orphan cleanup (Operator), mặc định xem trước:

~~~powershell
docker compose run --rm ops python -m citizen_ai.cli ops sweep-orphans --tenant TENANT_SLUG
~~~

Chỉ thêm --apply sau khi kiểm danh sách đúng tenant; grace tối thiểu 24 giờ. Không dùng lệnh này để xóa tri thức có DB reference hoặc xóa toàn bucket.
