# M2 lịch sử → kế hoạch P1/P2 v2.0

Cập nhật 13/11/2026. Phạm vi hiện hành chỉ là chatbot hỏi đáp công khai đa phường/xã.

M2 v1 đã có upload/private storage/ClamAV/parser/OCR/review/version/locator/purge và lexical/pgvector/hybrid với test local lịch sử. Chưa có live semantic acceptance và chưa nghiệm thu mọi crash/race/corpus phức tạp.

Kế hoạch còn lại được chuyển vào:
- [P1/W-03–W-09](IMPLEMENTATION_PLAN.md): corpus, metadata, batch idempotency, parser/review/version/pagination, hard-crash/race/purge/sweeper.
- [P2/W-10–W-16](IMPLEMENTATION_PLAN.md): query embedding ngoài transaction, retrieval/answer/history, evaluation và preflight.
- [P3–P5](IMPLEMENTATION_PLAN.md): nhúng khác origin, vận hành và UAT hỏi đáp công khai.

Bản M2_PLAN cũ giữ tại [archive](archive/2026-11-10-v1/M2_PLAN.md). Không thực hiện Actions/citizen login/voice/crawler như phần tiếp nối bắt buộc của M2.

Đọc master spec v2, IMPLEMENTATION_STATUS, REQUIREMENTS_CHECKLIST và TEST_REPORT trước code. Lượt cập nhật này chỉ tài liệu, chưa chạy lại test hoặc đổi code.
