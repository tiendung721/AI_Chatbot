# Hướng dẫn dự án

Đọc `CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md` và `docs/IMPLEMENTATION_STATUS.md` trước khi tiếp tục.

- Model/provider/keys và tham số AI chỉ do Developer cấu hình ở backend. Admin DTO từ chối trường lạ; không lộ cấu hình kỹ thuật qua API/UI.
- Tenant được xác định phía server; PostgreSQL RLS bắt buộc, runtime role không sở hữu bảng/không BYPASSRLS. Không dùng SQLite thay test RLS.
- Tri thức nháp không dùng cho công dân. Release bất biến; thu hồi hiện tại luôn thắng rollback/lịch sử.
- Action ghi cần xác thực và xác nhận; Preview không ghi thật. Không giả thành công khi chưa tích hợp.
- Mock và fixture phải có nhãn, bị chặn ở production. Không ghi secrets vào Git/logs.
- Không reset Git, xóa volume, tự public máy, tạo tài nguyên tính phí hoặc push Git.
- Windows: `./scripts/bootstrap.ps1`, `./scripts/dev.ps1`, `./scripts/check.ps1`.
- Linux: `bash scripts/bootstrap.sh`, `bash scripts/dev.sh`, `bash scripts/check.sh`.
- Cập nhật test report/status/resume bằng bằng chứng thực tế; không gọi một milestone là toàn bộ sản phẩm.
