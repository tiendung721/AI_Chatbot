# M2 — tài liệu và retrieval

Mở rộng M0/M1, giữ nguyên dữ liệu và cấu hình đang có. Chưa đánh dấu M2 hoàn tất cho tới khi có kết quả thật.

1. Migration tiến: metadata file, sections/locator/review, ingestion/deletion jobs + outbox, embedding profiles/vectors với RLS/composite FKs.
2. Upload từng file vào bucket private; MIME/magic/size/archive validation; ClamAV thật bắt buộc. Không bỏ scanner khi lỗi.
3. Parser/OCR tách container mạng nội bộ, không có secrets/database; CPU/RAM/time/output limits. PDF/DOCX/XLSX/PPTX/TXT/MD/CSV/HTML/PNG/JPG có fixture thật.
4. Preview extraction, warnings, chọn sheet/phần và duyệt revision; chỉ nội dung đã duyệt mới index/approve/publish.
5. Worker idempotent/lease/fencing; retry đúng version, không ghi đè bản xuất bản. Purge object/sections/chunks/vectors/derived answers và giữ tombstone tối thiểu.
6. Vector profile/adapter/hybrid có ACL trước tìm kiếm; disabled mặc định để không gọi API tính phí. Contract tests tách live semantic evaluation.
7. UI upload/progress/review/retry/version/source locator; regression M1, integration scanner/storage/worker và browser E2E.

Nguồn đã đối chiếu: https://docs.clamav.net/manual/Installing/Docker.html ; https://openpyxl.readthedocs.io/en/3.1/api/openpyxl.reader.excel.html ; https://pypdfium2.readthedocs.io/en/stable/python_api.html .
