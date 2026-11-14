# Theo dõi nghiệm thu M0–M2 local

Trạng thái và giới hạn từng REQ/CAP/UI: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

56 backend tests và 6 browser tests đạt không đồng nghĩa đã hoàn thành cả 70 kịch bản. `in_progress` gồm phần đã triển khai/kiểm thử một phần; `not_started` không phải test đạt. Bằng chứng chỉ trong phạm vi fixture/local được ghi, không thay thế nghiệm thu dữ liệu thật. Đường dẫn dưới đây tính từ apps/api/tests, trừ khi ghi rõ vị trí khác.

| Mã | Kịch bản | Trạng thái | Bằng chứng / việc còn lại |
|---|---|---|---|
| T-01 | Admin A mở document B bằng ID | implemented_and_tested | integration/test_m1.py::test_cross_tenant_document_api_and_composite_fk |
| T-02 | Admin A attach document_version B vào release A | implemented_and_tested | integration/test_m1.py::test_cross_tenant_document_api_and_composite_fk |
| T-03 | RAG A với câu hỏi trùng nội dung B | implemented_and_tested | integration/test_m1.py::test_rag_and_sources_are_isolated |
| T-04 | Worker thiếu TenantContext | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-05 | Reuse connection pool A rồi B | implemented_and_tested | integration/test_m1.py::test_runtime_role_rls_default_deny_and_connection_pool |
| T-06 | Citation/artifact/session IDs của người khác | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-07 | Cache cùng câu hỏi ở hai tenant | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-08 | SSE reconnect tới turn khác | implemented_and_tested | integration/test_m1.py::test_sse_replay_feedback_and_ownership |
| T-09 | Runtime role đọc DB không context | implemented_and_tested | integration/test_m1.py::test_runtime_role_rls_default_deny_and_connection_pool |
| T-10 | Admin PATCH chứa model/provider/API key | implemented_and_tested | unit/test_policy.py::test_admin_rejects_technical_fields; integration model injection test |
| T-11 | Instructions yêu cầu đổi model | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-12 | Admin export/dashboard/preview/errors | implemented_and_tested | integration/test_m1.py::test_no_technical_metadata_in_admin_public_and_errors (current M1 endpoints) |
| T-13 | Developer đổi chat model | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-14 | Đổi embedding dimension | implemented_and_tested | integration/test_m2.py::test_actual_pgvector_profiles_rls_and_filtered_hybrid; fingerprint/dimension mismatch chặn dùng index khác hệ quy chiếu, không chứng minh semantic quality |
| T-15 | Admin bật capability chưa cấp | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-16 | Capability không tương thích runtime | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-17 | Upload PDF nhiều trang | implemented_and_tested | unit/test_ingestion.py::test_real_formats_preserve_text_and_locators + test_parser_subprocess_and_limits; PDF 2 trang và page-limit failure, không âm thầm bỏ trang |
| T-18 | PDF scan tiếng Việt | implemented_and_tested | unit/test_ingestion.py::test_real_vietnamese_ocr_requires_review; PDF scan/PNG/JPG, Tesseract vie+eng thật trong Docker, locator/warning đúng |
| T-19 | XLSX nhiều sheet/merged/formula/hidden | implemented_and_tested | unit real XLSX + table context chunk test; integration/test_m2.py::test_xlsx_review_revision_ownership_and_no_hidden_leak; E2E Excel review, không tính lại formula |
| T-20 | File giả MIME, quá lớn, nén độc hại | implemented_and_tested | unit/test_ingestion.py::test_upload_magic_archive_xml_and_size_fail_closed; ClamAV EICAR/quarantine integration; chưa fuzz/security scan production |
| T-21 | File chứa script/macro/prompt injection | in_progress | HTML scripts bị loại/XML entity bị chặn; parser tách mạng/resources. Chưa nghiệm thu prompt injection với live AI/macro/security corpus đầy đủ |
| T-22 | Upload cùng file/retry worker | in_progress | process_ingestion chạy hai lần không nhân chunks/version; retry scanner có test; chưa có request idempotency cho batch upload nên không đánh dấu đạt toàn kịch bản |
| T-23 | Job worker crash và chạy lại | in_progress | Code có lease/fencing và outbox + worker queue thật; chưa kill worker giữa parse/purge để nghiệm thu hard crash |
| T-24 | Tài liệu draft chưa publish | implemented_and_tested | integration draft preview/public isolation + tests/e2e/m1.spec.ts |
| T-25 | Publish khi file chưa ready | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-26 | Publish đồng thời hai tab | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-27 | Rollback nội dung | implemented_and_tested | integration/test_m1.py::test_releases_are_immutable_and_rollback_does_not_change_runtime |
| T-28 | Thu hồi tài liệu giữa lúc generate | implemented_and_tested | integration/test_m1.py::test_revocation_during_generation_and_rollback_blocked |
| T-29 | Metadata hiệu lực không rõ/mâu thuẫn | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-30 | Không có nguồn | implemented_and_tested | integration draft/public no-evidence case + Mock contract test |
| T-31 | Model tạo evidence ID/URL giả | implemented_and_tested | unit/test_policy.py::test_source_validator_rejects_fabricated_or_missing_evidence |
| T-32 | DOCX không pagination | implemented_and_tested | unit/test_ingestion.py::test_real_formats_preserve_text_and_locators (.docx): sections/headings/table/header, không page number giả |
| T-33 | Query tiếng Việt không dấu/lỗi gõ | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-34 | Website mới/sửa/xóa/redirect | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-35 | Website timeout/403 | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-36 | SSRF tới localhost/private/metadata/IPv6 | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-37 | DNS rebinding/redirect ngoài allowlist | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-38 | HTML XSS/source link nguy hiểm | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-39 | Anonymous gọi personal tool | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-40 | Citizen A biết mã hồ sơ B | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-41 | Fake issuer/audience/nonce/expired OIDC | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-42 | Gửi Action chưa confirm | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-43 | Confirm nonce hết hạn/dùng lại | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-44 | Sửa payload sau confirm | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-45 | Double-click confirm cùng payload | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-46 | Upstream write timeout sau tiếp nhận | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-47 | Playground chạy write tool | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-48 | API nghiệp vụ chưa cấu hình | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-49 | Provider 429/timeout/invalid model | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-50 | Tool loop quá giới hạn | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-51 | Structured output refusal/incomplete | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-52 | Gửi lại POST message cùng request ID | implemented_and_tested | integration/test_m1.py::test_idempotency_conflict_and_single_live_turn |
| T-53 | Mất SSE/kết nối lại | implemented_and_tested | integration/test_m1.py::test_sse_replay_feedback_and_ownership (DB replay/terminal recovery) |
| T-54 | Cancel khi Action đã gửi | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-55 | Nhiều request tiêu budget cùng lúc | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-56 | Không có pricing entry | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-57 | Production dùng mock/default secrets | implemented_and_tested | unit/test_policy.py::test_startup_fails_closed; runtime role checks |
| T-58 | Purge attachment/chat/document | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-59 | Backup restore | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-60 | UI desktop và mobile | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
| T-61 | Admin A thử tenant switch/body tenant_id | implemented_and_tested | integration unknown tenant field/foreign version rejection + browser fixed-tenant UI |
| T-62 | Thu hồi Action trong phiên đang mở | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-63 | Attachment user vào public Knowledge | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-64 | Web search mang thông tin cá nhân | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-65 | Code sandbox đọc secret host | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-66 | Voice/image capability chưa configured | not_started | Triển khai và kiểm thử theo milestone tương ứng trong đặc tả. |
| T-67 | Bootstrap lần hai | implemented_and_tested | scripts/verify_bootstrap.py before/after a real second scripts/bootstrap.ps1 run |
| T-68 | Docker Engine chưa chạy trên Windows | implemented_and_tested | PowerShell isolated docker command failure stub; engine itself was not stopped; TEST_REPORT.md |
| T-69 | Model/capability raw fields ở browser response | implemented_and_tested | integration filtered response key checks + browser Admin API injection test (M1 scope) |
| T-70 | Schema API sinh TypeScript | in_progress | Có implementation/kiểm thử một phần; hoàn thiện toàn bộ kịch bản tại M2–M7 trước khi đánh dấu đạt. |
