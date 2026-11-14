# Corpus công khai cho kiểm thử P1

catalog.json là danh mục URL được tuyển chọn; manifest.json ghi snapshot đã tải, provenance, SHA256, format, phạm vi và tenant fixture. Mọi nguồn đều có nhãn technical_test_only_not_approved, không phải dữ liệu đã nghiệm thu pháp lý hoặc đã được phép xuất bản cho công dân.

22 file gốc duy nhất: 9 PDF, 8 DOCX, 3 XLSX, 2 HTML; khoảng 10,4 MB. Hai tenant public-test-a/b chỉ là nhãn phân bổ fixture. Tài liệu Xuân Định thuộc public-test-b; không coi nguồn địa phương đó áp dụng cho tenant khác. Các văn bản cũ/chưa hiệu lực được giữ để thử định dạng và trạng thái, không dùng làm hướng dẫn hiện hành.

Chạy từ root khi được phép truy cập Internet:

```powershell
python scripts/collect_public_corpus.py
```

Collector chỉ truy cập catalog cố định, HTTPS/exact-host allowlist, kiểm public DNS/redirect, timeout, tối đa 30 nguồn và 25 MiB/file. Không crawler, không tự publish, không kết nối AI. File tải nằm trong .local/public-corpus, được Git bỏ qua. Tên file có hash, không ghi đè snapshot khác nội dung.

Test opt-in: apps/api/tests/integration/test_public_corpus.py; PUBLIC_CORPUS_DIR trỏ vào thư mục chứa manifest/file, PUBLIC_CORPUS_REPORT trỏ nơi lưu JSON. Dùng stack PostgreSQL/storage/ClamAV/parser thật; chỉ tenant fixture, không sửa dữ liệu người dùng. Hướng dẫn lệnh đầy đủ và kết quả tại docs/EXTRACTION_REPORT.md.

Trang DVC-01 yêu cầu JavaScript và snapshot không có text thủ tục: kỳ vọng EXTRACTION_EMPTY, được báo là thất bại trích xuất có dự kiến, không cộng vào file trích xuất thành công. Ảnh DERIVED-SCAN-01 được render từ trang đầu CB-05 trong test, có nhãn ảnh scan dẫn xuất, không giả là file scan gốc cơ quan phát hành.

DOCX ký số có thể dùng đường dẫn Windows trong ZIP. Parser chuẩn hóa bản sao trong bộ nhớ và cảnh báo; file gốc giữ nguyên hash. Hệ thống không xác minh giá trị chữ ký số. Số liệu trích xuất không chứng nhận mọi bảng/layout hoặc đáp án nghiệp vụ đúng; đánh giá live AI thuộc P2/P5.
