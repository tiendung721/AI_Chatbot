# Hướng dẫn dự án — phạm vi v2.0

Đọc CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md, docs/IMPLEMENTATION_STATUS.md và docs/IMPLEMENTATION_PLAN.md trước khi tiếp tục. V2 là nguồn hiện hành; docs/archive chỉ là lịch sử.

- Sản phẩm: chatbot hỏi đáp công khai đa phường/xã, Admin quản lý tri thức văn bản/file/OCR/review/publish, nguồn dẫn và widget nhúng khác origin.
- Ngoài phạm vi: đăng nhập công dân/OIDC, hồ sơ cá nhân, Actions/phản ánh/đặt lịch, citizen attachments, web search/crawler, voice/image/code/MCP. Không tái yêu cầu các tích hợp này để nghiệm thu v2.
- Model/provider/keys và tham số AI chỉ do Developer cấu hình backend. Admin DTO từ chối trường lạ; không lộ cấu hình kỹ thuật qua API/UI.
- Tenant xác định phía server; PostgreSQL RLS bắt buộc. Runtime không sở hữu bảng/không BYPASSRLS; không dùng SQLite thay test RLS.
- Tri thức nháp không dùng cho công dân. Release bất biến; thu hồi hiện tại luôn thắng rollback/lịch sử. Preview không tạo thay đổi public.
- Không giả thành công/live verification khi chưa tích hợp hoặc chưa chạy. Mock/fixture có nhãn và bị chặn production.
- Bảo mật Admin/MFA, giới hạn chi phí cơ bản, retention/load/backup/restore và nghiệm thu cổng thật vẫn là phần v2 cần đạt.
- Không reset Git, xóa volume, tự public máy, tạo tài nguyên tính phí hoặc push Git. Không ghi secrets vào Git/logs.
- Windows: ./scripts/bootstrap.ps1, ./scripts/dev.ps1, ./scripts/check.ps1.
- Linux: bash scripts/bootstrap.sh, bash scripts/dev.sh, bash scripts/check.sh.
- Theo dõi phase P0–P5 và AT-01–AT-45; cập nhật report/status/resume bằng bằng chứng thực. M0–M8/T-ID cũ chỉ đối chiếu lịch sử.
- W-01 đã thay scripts/update_requirement_checklist.py bằng validator FR/NFR/W/AT chỉ đọc. Không dùng tool để ghi đè checklist hoặc tự suy kết quả pass.
- P0 đã hoàn tất tài liệu trước code; người dùng đã yêu cầu triển khai P1/W-01–W-09. Đọc report/status/resume để tiếp tục đúng mốc; không tự coi P1 là toàn bộ sản phẩm đã hoàn thành.
