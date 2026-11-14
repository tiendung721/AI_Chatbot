# Điểm tiếp tục — M2 local

Đọc master spec, AGENTS, IMPLEMENTATION_STATUS, REQUIREMENTS_CHECKLIST, TEST_REPORT và Git diff trước khi sửa. Source mới còn chưa commit; không reset/ghi đè. `.env`, `.local`, test trace có secrets/fixture credentials, không công bố hoặc đưa vào Git.

## Đã triển khai

M0/M1 vẫn hoạt động: tenant RLS, Admin auth/password/session, văn bản/version, builder/Preview, release immutable/rollback, chat/retrieval/citations/SSE/feedback và widget.

M2 có migration 0003; upload batch vào MinIO private, ClamAV thật fail closed, parser/OCR tách mạng/không secrets, PDF/DOCX/XLSX/PPTX/TXT/MD/CSV/HTML/PNG/JPG. Có sections/locator, warnings/OCR/hidden sheets/formula cached value, review edits/revision, metadata cơ bản, file version mới, retry, public approval, source view và purge job xóa dữ liệu dẫn xuất. Bảng Excel/CSV chia chunk theo hàng, lặp context; hàng quá rộng trả lỗi rõ.

pgvector exact cosine + RRF/lexical đã test với PostgreSQL thật; profiles Developer-only, vectors tenant RLS, dimension/fingerprint gates. Embeddings mặc định disabled. OpenAI adapters chỉ contract test; chưa paid/live calls hoặc semantic acceptance. Không thay `.env` hoặc mật khẩu người dùng. E2E dùng manifest mới chỉ chứa tenant fixture của chính lần chạy; dữ liệu fixture cũ không bị trộn vào lần sau.

Hướng dẫn thao tác: ADMIN_GUIDE.md. Cấu hình/reindex có thể tính phí: OPERATIONS.md. Kết quả và giới hạn thực tế: TEST_REPORT.md.

## Cần hoàn tất/kiểm chứng tiếp

1. Semantic evaluation tiếng Việt với model thật và bộ nguồn nghiệp vụ được phép gửi ra provider; chưa có key/model/data/UAT. Không dùng mock vectors để nghiệm thu chất lượng.
2. Tài liệu thực tế nhiều cột/bảng phức tạp, header/unit ambiguity, toàn bộ metadata/tags/supersedes, lọc/phân trang kho và so sánh phiên bản. Bản hiện tại chỉ hiển thị tối đa 200 phiên bản.
3. Hard-crash/lease recovery có kill process thật, concurrent review/revoke/purge races, fuzz/corpus lớn, resource/load benchmarks và security scan; hiện có idempotency/fencing code và integration coverage nhưng chưa nghiệm thu hết trường hợp này.
4. Tách query embedding ra khỏi transaction retrieval và đo pool/latency; reindex cho nguồn chưa công khai/Preview theo data policy; quota/pricing/usage embeddings M6. Reindex hiện chỉ nguồn đã duyệt công khai và phải được Developer gọi rõ.
5. Orphan sweeper, retention, backup/provider deletion, kiểm tra tombstone sau restore M6/M7. Purge hiện chỉ chứng minh kho đang hoạt động, không chứng nhận xóa mọi bản sao.
6. Tiếp M3–M8 theo đặc tả: website sync/eval/trace/diff, Actions/IdP/API nghiệp vụ, capabilities nâng cao, quota/monitoring/security/production/UAT. Không gọi M2 là full product.

## Tiếp tục local

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
npx --yes pnpm@12.18.0 test:e2e
```

`check`/E2E yêu cầu local/test + Mock AI + disabled embeddings. Không tự sửa cấu hình live để làm test pass. Docker Desktop cần đủ RAM cho ClamAV/OCR. Không stop/reset volume, mở internet, push hoặc gọi API tính phí khi chưa được yêu cầu.
