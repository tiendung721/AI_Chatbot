# API hiện có — sau P1 local, phạm vi sản phẩm v2

Đặc tả v2/P0–P5 là target; tài liệu này mô tả routes đã có, chưa bao gồm mọi target API. Citizen auth/Actions/crawler/voice/images là out_of_scope, không phải backlog bắt buộc. Tool sinh TypeScript giữ theo OpenAPI thực, không theo endpoint dự kiến trong đặc tả.

OpenAPI thật được sinh từ FastAPI tại `/api/v1/openapi.json`; Swagger UI local ở `/api/v1/docs`. `scripts/export_openapi.py` xuất schema không cần credential/provider call; `pnpm generate:api` sinh `packages/api-client/schema.d.ts`, frontend sử dụng types request/config/result.

Nhóm đã triển khai: Admin login/me/change-password/logout; assistant/draft/preview; Knowledge văn bản/phiên bản/approve/revoke; validate/publish/history/rollback; pause/dashboard/audit/capability status; public assistant/session; turns/result/events/cancel/feedback; nguồn dẫn theo ownership. Chi tiết route và DTO xem schema sinh, không coi các endpoint ở đặc tả là đã tồn tại nếu chưa có code.

Admin dùng HttpOnly cookie và `X-CSRF-Token` + Origin cho request ghi. Token CSRF lấy từ login hoặc `/auth/me`; không nằm trong URL. Anonymous/Preview chat dùng `Authorization: Bearer <session_token>` trong bộ nhớ, không localStorage/query string.

PATCH draft và validate/publish yêu cầu `If-Match: "<revision>"`. Trường lạ bị từ chối; lỗi validation không echo lại key/giá trị nhạy cảm. Body của API nội bộ có giới hạn qua Nginx. Lỗi có `code`, `message`, `request_id`, `retryable`; không trả raw provider errors.

POST turn nhận `client_request_id` UUID; trùng key/cùng payload trả cùng turn, payload khác trả 409. Tối đa một lượt đang xử lý/session. SSE có event IDs và Last-Event-ID, xác thực lại khi reconnect. Kết quả cuối đọc lại được từ DB. Source viewer cần token đúng phiên, kiểm tra lại nguồn thu hồi/hết hiệu lực.

Kho tri thức và lịch sử phiên bản đã phân trang trong P1. Release/audit vẫn tối đa 100; pagination và response models cho mọi nhóm endpoint chưa hoàn thành. Crawler/OIDC/Actions/voice/images ngoài phạm vi v2.

## File Knowledge

Prefix `/api/v1/admin/knowledge`; mọi route dùng phiên Admin/tenant server-side. Upload multipart nhận `files` (tối đa 10), `document_id` tùy chọn (một file khi tạo phiên bản mới) và `client_request_id` UUID. Client P1 giữ cùng ID và payload khi retry; ID khác payload nhận 409. Trường ID tạm thời optional để tương thích client cũ; bỏ ID không được bảo đảm dedupe giữa hai POST. Kết quả 202 có trạng thái/job/version cho từng file; `rejected` không phải đã xử lý thành công. Endpoint này có cap tổng 251 MiB ở gateway và giới hạn stream thực tế ở API; từng file tối đa 25 MiB. Các JSON requests khác vẫn giới hạn 512000 bytes.

| Route | Tác dụng |
|---|---|
| `GET /documents` | Kho phiên bản: page/page_size (mặc định 1/20, tối đa 100), q, status, approved, file_type, effectivity; trả items/total/page/page_size/next_cursor |
| `GET /documents/{id}` | Lịch sử cùng tài liệu, page/page_size như kho; không trả toàn bộ body trong danh sách |
| `POST /documents/{id}/versions` | Tạo phiên bản văn bản mới; không đổi release đang phục vụ |
| `POST /uploads` | Upload batch, private quarantine; trả job IDs |
| `GET /jobs/{id}` | Tiến độ/error_code/attempts |
| `POST /jobs/{id}/retry` | Thử lại job failed còn hợp lệ; không bypass cách ly |
| `GET /versions/{id}` | Metadata cơ bản/sections/locator/warnings, không object key hoặc URL nội bộ |
| `PATCH /versions/{id}/metadata` | Strict DTO revision + document_number/issuer/issued_on/effective_from/effective_to/source_url/collected_on/jurisdiction/classification/topic_tags/supersedes_version_id/allow_public_download; từ chối bản đã xuất bản |
| `GET /versions/{id}/diff?against=UUID` | So sánh body/metadata hai phiên bản cùng tài liệu và tenant; có báo truncated khi vượt giới hạn |
| `POST /versions/{id}/review` | Strict DTO extraction revision, section IDs cùng phiên bản, edits và xác nhận warnings |
| `GET /versions/{id}/original` | Attachment download qua xác thực, chỉ file scan sạch/chưa thu hồi |
| `POST /documents/{id}/delete-request` | Reason bắt buộc; thu hồi ngay rồi trả purge job ID |
| `GET /deletions/{id}` | queued/executing/completed/failed |

Job/file/version/section IDs không phải quyền truy cập. Approval chỉ nhận nguồn ready và clean/not_required. Nguồn sẵn sàng chưa vào release không được citizen retrieval. Citation/source response thêm `locator`; trường `section` giữ tương thích với client văn bản cũ.

Metadata unknown để null. source_url chỉ lưu HTTP(S) hợp lệ, không tải URL. jurisdiction là national/current_tenant; classification public/internal/restricted, chỉ public được approve công khai. supersedes phải là phiên bản cũ cùng tài liệu/tenant. Metadata/review thay đổi làm mất approval và tăng revision. allow_public_download hiện là chính sách lưu trữ; public source viewer vẫn trả excerpt, chưa có tính năng tải original công khai. Preview dùng provider ngoài chặn nguồn chưa được phép gửi trước khi gọi AI.

next_cursor hiện là số trang tiếp theo dạng chuỗi; client gửi lại bằng page. Kho sắp theo updated_at/id; dữ liệu thay đổi giữa các request có thể làm dịch trang, không phải snapshot bất biến. Diff giới hạn đầu vào 100.000 ký tự và 2.000 dòng/body, đầu ra tối đa 200.000 ký tự và báo cắt ngắn rõ ràng.

