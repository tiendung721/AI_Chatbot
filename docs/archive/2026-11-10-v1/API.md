# API M0–M2 local

OpenAPI thật được sinh từ FastAPI tại `/api/v1/openapi.json`; Swagger UI local ở `/api/v1/docs`. `scripts/export_openapi.py` xuất schema không cần credential/provider call; `pnpm generate:api` sinh `packages/api-client/schema.d.ts`, frontend sử dụng types request/config/result.

Nhóm đã triển khai: Admin login/me/change-password/logout; assistant/draft/preview; Knowledge văn bản/phiên bản/approve/revoke; validate/publish/history/rollback; pause/dashboard/audit/capability status; public assistant/session; turns/result/events/cancel/feedback; nguồn dẫn theo ownership. Chi tiết route và DTO xem schema sinh, không coi các endpoint ở đặc tả là đã tồn tại nếu chưa có code.

Admin dùng HttpOnly cookie và `X-CSRF-Token` + Origin cho request ghi. Token CSRF lấy từ login hoặc `/auth/me`; không nằm trong URL. Anonymous/Preview chat dùng `Authorization: Bearer <session_token>` trong bộ nhớ, không localStorage/query string.

PATCH draft và validate/publish yêu cầu `If-Match: "<revision>"`. Trường lạ bị từ chối; lỗi validation không echo lại key/giá trị nhạy cảm. Body của API nội bộ có giới hạn qua Nginx. Lỗi có `code`, `message`, `request_id`, `retryable`; không trả raw provider errors.

POST turn nhận `client_request_id` UUID; trùng key/cùng payload trả cùng turn, payload khác trả 409. Tối đa một lượt đang xử lý/session. SSE có event IDs và Last-Event-ID, xác thực lại khi reconnect. Kết quả cuối đọc lại được từ DB. Source viewer cần token đúng phiên, kiểm tra lại nguồn thu hồi/hết hiệu lực.

Giới hạn: danh sách tài liệu tối đa 200 version, release/audit tối đa 100; pagination đầy đủ và response models cho mọi nhóm endpoint chưa hoàn thành. Chưa có crawler/OIDC/Actions/voice/images.

## File Knowledge

Prefix `/api/v1/admin/knowledge`; mọi route dùng phiên Admin/tenant server-side. Upload multipart chỉ nhận `files` (tối đa 10) và `document_id` tùy chọn (một file khi tạo phiên bản mới). Kết quả 202 có trạng thái/job/version cho từng file; `rejected` không phải đã xử lý thành công. Endpoint này có cap tổng 251 MiB ở gateway và giới hạn stream thực tế ở API; từng file tối đa 25 MiB. Các JSON requests khác vẫn giới hạn 512000 bytes.

| Route | Tác dụng |
|---|---|
| `POST /uploads` | Upload batch, private quarantine; trả job IDs |
| `GET /jobs/{id}` | Tiến độ/error_code/attempts |
| `POST /jobs/{id}/retry` | Thử lại job failed còn hợp lệ; không bypass cách ly |
| `GET /versions/{id}` | Metadata cơ bản/sections/locator/warnings, không object key hoặc URL nội bộ |
| `PATCH /versions/{id}/metadata` | Strict DTO revision + document_number/issuer/issued_on/effective_from/effective_to; từ chối bản đã xuất bản |
| `POST /versions/{id}/review` | Strict DTO extraction revision, section IDs cùng phiên bản, edits và xác nhận warnings |
| `GET /versions/{id}/original` | Attachment download qua xác thực, chỉ file scan sạch/chưa thu hồi |
| `POST /documents/{id}/delete-request` | Reason bắt buộc; thu hồi ngay rồi trả purge job ID |
| `GET /deletions/{id}` | queued/executing/completed/failed |

Job/file/version/section IDs không phải quyền truy cập. Approval chỉ nhận nguồn ready và clean/not_required. Nguồn sẵn sàng chưa vào release không được citizen retrieval. Citation/source response thêm `locator`; trường `section` giữ tương thích với client văn bản cũ.
