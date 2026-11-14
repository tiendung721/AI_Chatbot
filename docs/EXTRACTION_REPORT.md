# Báo cáo trích xuất corpus công khai P1

Lượt 13/11/2026; dữ liệu công khai được tuyển cho kiểm thử kỹ thuật, không phải kho đã phê duyệt nghiệp vụ. Report JSON gốc: .local/p1-corpus-report.json. Nguồn/hash: [manifest](../fixtures/public_sources/manifest.json), [catalog](../fixtures/public_sources/catalog.json).

## Kết quả đã chạy

22 file gốc, 22 SHA256 khác nhau, 7 nhóm chủ đề, hai tenant fixture; 9 PDF, 8 DOCX, 3 XLSX, 2 HTML, tổng 10.364.405 bytes. Có thêm một ảnh OCR dẫn xuất từ trang đầu CB-05, gắn nhãn DERIVED-SCAN-01 riêng.

21/22 file gốc trích xuất được; một HTML chỉ có JavaScript trả EXTRACTION_EMPTY đúng dự kiến. Tính cả ảnh dẫn xuất: 10 ready, 12 needs_review và 1 failed có dự kiến. 9 PDF có tổng 508 trang được parser báo đọc đủ. Việc báo đủ trang không chứng minh mọi bảng/layout đã được hiểu đúng nghiệp vụ.

Bài test upload → private storage → ClamAV thật → parser subprocess thật → metadata/sections và kiểm tra chéo tenant đã chạy đạt: 1 corpus test, 94,30 giây ở lần chạy cuối ghi report này (JSON bắt đầu 08:23:45 UTC). Tổng thời gian đo từng file 88,000 giây; đây là phép đo tuần tự local, không phải benchmark tải hay SLA. Không gọi AI, không duyệt public và không publish corpus.

## Từng trường hợp

| ID | Định dạng | Trạng thái | Phần đọc được | Thời gian giây | Ghi chú |
|---|---|---|---|---|---|
| CB-01 | .docx | needs_review | 16 | 2.939 | Có cảnh báo, cần duyệt |
| CB-02 | .docx | needs_review | 4 | 1.387 | Có cảnh báo, cần duyệt |
| CB-03 | .docx | needs_review | 52 | 4.535 | Có cảnh báo, cần duyệt |
| CB-04 | .docx | needs_review | 5 | 1.843 | Có cảnh báo, cần duyệt |
| CB-05 | .pdf | ready | 222 | 28.540 |  |
| CB-06 | .pdf | ready | 61 | 6.133 |  |
| CB-08 | .pdf | ready | 47 | 3.561 |  |
| CB-09 | .pdf | ready | 31 | 3.753 |  |
| CB-10 | .pdf | needs_review | 76 | 5.795 | Có cảnh báo, cần duyệt |
| CB-11 | .pdf | ready | 18 | 2.485 |  |
| CB-12 | .docx | needs_review | 34 | 3.088 | Có cảnh báo, cần duyệt |
| CB-13 | .pdf | needs_review | 41 | 4.332 | Có cảnh báo, cần duyệt |
| CB-14 | .pdf | needs_review | 10 | 2.479 | Có cảnh báo, cần duyệt |
| CB-15 | .docx | needs_review | 5 | 1.533 | Có cảnh báo, cần duyệt |
| CB-16 | .docx | needs_review | 158 | 3.617 | Có cảnh báo, cần duyệt |
| CB-17 | .docx | needs_review | 5 | 2.599 | Có cảnh báo, cần duyệt |
| XD-01 | .pdf | ready | 2 | 1.252 |  |
| XD-02 | .xlsx | ready | 11 | 1.291 |  |
| XD-03 | .xlsx | ready | 8 | 1.296 |  |
| XD-04 | .xlsx | ready | 3 | 1.028 |  |
| DVC-01 | .html | failed | 0 | 0.801 | EXTRACTION_EMPTY |
| XD-HTML | .html | ready | 1 | 0.950 |  |
| DERIVED-SCAN-01 | .png | needs_review | 1 | 2.763 | Ảnh scan dẫn xuất có nhãn |

## Các lỗi thực tế đã phát hiện và sửa

- DOCX ký số có đường dẫn ZIP kiểu Windows bị từ chối trên Linux: normalize bản sao trong parser, vẫn kiểm traversal/collision/bomb/XML, không thay bytes file gốc; cảnh báo chữ ký chưa được xác minh.
- PDF CB-10 trích ra ký tự điều khiển không hợp lệ với PostgreSQL: loại control chars không dùng, chuẩn hóa Unicode và thêm warning bắt buộc review.
- Snapshot DVC-01 không có text thủ tục do phụ thuộc JavaScript: giữ ca lỗi, không công bố thành trích xuất thành công. Phiên bản v2 không có headless crawler hoặc tự chạy JavaScript nguồn.

Các văn bản lịch sử/chưa hiệu lực không trở thành hướng dẫn hiện hành chỉ vì parser đọc được. Metadata nguồn có ngày chưa xác minh để null và review_status technical_test_only_not_approved.

## Tái lập

Từ root, tải corpus bằng python scripts/collect_public_corpus.py. Không tự bật embeddings hoặc AI thật. Lệnh test Windows:

~~~powershell
docker compose run --rm --no-deps -v D:/Work/Project/AI_Chatbot/apps/api:/workspace -v D:/Work/Project/AI_Chatbot/.local/public-corpus:/corpus:ro -v D:/Work/Project/AI_Chatbot/.local:/evidence -w /workspace -e PYTHONPATH=/workspace/src -e PUBLIC_CORPUS_DIR=/corpus -e PUBLIC_CORPUS_REPORT=/evidence/p1-corpus-report.json tests pytest -q -s -p no:cacheprovider tests/integration/test_public_corpus.py
~~~

Điều chỉnh bind path khi workspace khác. Các test dùng tài khoản/tenant fixture mới; không nạp corpus vào đơn vị người dùng. Raw documents/credentials/trace nằm trong .local và không đưa vào Git.

## Chưa chứng minh

Chất lượng trả lời AI, semantic recall, tính đúng pháp lý hiện hành, chữ ký số, layout phức tạp ngoài corpus, tải đồng thời, Linux host độc lập, policy provider/backup/retention và UAT. Đây là bằng chứng W-03/W-06 trong P1; các gate G2–G5 vẫn riêng.

