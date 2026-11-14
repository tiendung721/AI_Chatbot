# Phụ thuộc bên ngoài v2.0

Cập nhật 13/11/2026. Các đầu vào dưới đây cần ở giai đoạn sử dụng; chưa ngăn chuẩn bị tài liệu hoặc lập trình/kiểm thử local. Không yêu cầu đăng nhập công dân/IdP/API hồ sơ/Actions cho bản này.

| Mã | Đầu vào | Hiện trạng đã biết | Cần trước | Vẫn làm được khi thiếu |
|---|---|---|---|---|
| E-01 | Địa phương mục tiêu, đầu mối quản trị/review nội dung | Chưa chỉ định trong hội thoại | Corpus nghiệp vụ nghiệm thu và P5 | Tự tuyển nguồn công khai quốc gia/địa phương có nhãn, fixture và UI |
| E-02 | AI key/model/embedding profile, bảng giá chính thức, budget và quyền gọi paid API | Chưa được cấp/xác minh trong dự án | Live P2/G2 và paid production | Contract/Mock/local lexical/vector fixture; không tự bật API |
| E-03 | Policy gửi dữ liệu tới AI, phân loại nguồn/PII/provider retention | Chưa được đơn vị phê duyệt | Gọi AI thật với corpus và public rollout | Soạn data-flow/policy, test local dữ liệu được phép |
| E-04 | Corpus chính thức và bộ câu hỏi có người chấm nghiệp vụ | Chưa có bộ được đơn vị chấp thuận | G2/P5 | Bộ nguồn/câu hỏi ứng viên, không gọi là đã nghiệm thu |
| E-05 | Domain chatbot, domain cổng, TLS và người có quyền chỉnh snippet/CSP cổng | Chưa cung cấp | G5/cổng thật | Hai origin local mô phỏng/P3, hướng dẫn tích hợp |
| E-06 | Host/network/storage/backup/monitoring, người vận hành và người ký UAT | Chưa chọn/cấp | Đo/triển khai thực tế P4/P5 | Template deploy, report local và runbooks |

## Quyết định đã có, không cần xin lại

- Người dân không đăng nhập; không cần OIDC/VNeID hoặc API tra cứu/nộp hồ sơ.
- Admin upload/nhập tri thức thủ công; website sync và live web search ngoài scope v2.
- Có thể tự tìm nguồn công khai để chuẩn bị corpus local. Việc tìm nguồn không tự cấp quyền publish cho công dân hoặc gửi mọi nội dung tới AI bên ngoài.
- Phạm vi hiện tại chỉ tài liệu; chưa triển khai/mua tài nguyên, không public máy hoặc push Git.

## Đầu vào kỹ thuật triển khai

- Storage local hiện build MinIO từ source có checksum. License/CVE/maintenance phải review trước production; không mặc định triển khai nguyên cấu hình local.
- Chọn model/giá sau khi xác minh tài liệu chính thức, không lấy tên model và giá từ ví dụ hoặc suy đoán.
- Hạ tầng nhỏ dùng single-host Docker + backup, mục tiêu RPO24h/RTO4h cần đo. Không mặc định đã HA.
- Giá trị retention 30/180/365 ngày và backup30 ngày trong spec là mặc định lập kế hoạch, đơn vị cần duyệt theo mục đích/hạ tầng thực.
