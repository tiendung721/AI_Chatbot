# Hướng dẫn Admin — văn bản và file

1. Mở `/admin`; lấy tài khoản local trong `.local/provisioned-admins.json`. Đăng nhập và đổi mật khẩu cấp lần đầu.
2. Vào **Kho tri thức**. Có thể soạn văn bản rồi **Lưu văn bản**, hoặc **Chọn file** trong vùng tải lên. Hỗ trợ PDF/DOCX/XLSX/PPTX/TXT/MD/CSV/HTML/PNG/JPG; tối đa 25 MB/file, 10 file/lượt. Theo dõi tiến độ quét virus/trích xuất; file lỗi hoặc cách ly không được đưa vào chatbot.
3. Kiểm tra nội dung và xác nhận **được phép công khai**; không xác nhận nếu có dữ liệu cá nhân chưa được phép công bố.
4. Vào **Cấu hình chatbot**, chọn phiên bản văn bản, chỉnh tên/lời chào/Instructions/câu gợi ý, bấm **Lưu nháp**. Preview chỉ dùng bản nháp đã lưu.
5. Hỏi thử trong **Xem thử trợ lý**, mở thẻ nguồn để kiểm tra nội dung. Đây là Preview nội bộ, không tác động bản đang phục vụ.
6. Vào **Kiểm tra & xuất bản**, chạy kiểm tra, nhập lý do và bấm **Xuất bản nội dung**. Kiểm tra tối thiểu M1 chưa thay thế đánh giá nghiệp vụ hoặc chất lượng AI thật.
7. Bấm **Mở trang công dân** để kiểm tra release. Người dân hỏi không cần đăng nhập; các nghiệp vụ hồ sơ cá nhân chưa được cấu hình và không trả kết quả giả.

**Thu hồi** chặn tài liệu ngay cho lượt trả lời mới và source viewer; không phải xóa vĩnh viễn. **Khôi phục** tạo một release mới, kiểm tra nguồn/quyền hiện tại và không đổi cấu hình AI. **Tổng quan** có tạm dừng/tiếp tục và nhật ký.

Không có màn hình chọn model/provider/API key. Đồng bộ website, Actions và các chức năng nâng cao còn ở milestone sau; chưa phải toàn bộ Admin Portal hoàn chỉnh.

## Kiểm tra tài liệu tải lên

Chọn **Xem nội dung** ở đúng phiên bản. Đối chiếu nội dung với file gốc đã quét sạch; hệ thống hiển thị vị trí trang PDF, sheet/vùng ô, slide hoặc mục. DOCX không có số trang giả.

Ảnh/PDF scan luôn yêu cầu kiểm tra OCR. Excel hiển thị sheet ẩn và cảnh báo công thức thiếu cached value; hệ thống không tự tính công thức. Sheet ẩn mặc định không được chọn. Mở từng phần, chọn phạm vi muốn dùng, sửa nội dung nếu cần, xác nhận đã kiểm tra rồi bấm **Duyệt nội dung và lập chỉ mục**. Quyết định được lưu theo revision; nếu báo xung đột hãy đóng và mở lại bản trích xuất.

Nhập số văn bản, cơ quan/ngày ban hành và khoảng hiệu lực tại **Thông tin văn bản và hiệu lực**. Ngày chưa rõ để trống. Lưu metadata sẽ yêu cầu xác nhận công khai lại. Phiên bản đã xuất bản được giữ nguyên; để thay đổi hãy **Thêm phiên bản file** rồi duyệt/xuất bản phiên bản mới. Phiên bản mới không tự thay bản đang phục vụ.

Job lỗi có thể **Thử lại xử lý** sau khi khắc phục. File cách ly không có nút bỏ qua scanner. Các mã `TABLE_ROW_LIMIT`/`TABLE_CONTEXT_LIMIT` yêu cầu chia bảng hoặc chuyển tài liệu sang cấu trúc rõ hơn; không có nội dung bị âm thầm cắt bỏ để báo thành công.

**Xóa dữ liệu** yêu cầu nhập lý do, thu hồi nguồn ngay và chạy job xóa file/chunks/vectors/sections/nội dung trả lời dẫn xuất trong kho đang hoạt động. Theo dõi đến khi hoàn tất; nếu lỗi có thể yêu cầu xóa lại. Tombstone/version IDs còn để giữ quan hệ lịch sử. Xóa khỏi backup/provider theo chính sách và kiểm tra sau restore chưa được nghiệm thu; không coi thông báo local là chứng nhận xóa mọi bản sao bên ngoài.
