# AI Cổng thông tin đa phường

Bản phát triển theo **đặc tả v2.0 ngày 13/11/2026** tại `CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md`. Hiện có tri thức văn bản và file → quét virus → trích xuất/OCR → kiểm tra nội dung → bản nháp → xuất bản → chat có nguồn. Có phiên bản tài liệu, thu hồi và xóa dữ liệu khỏi kho đang hoạt động. Dữ liệu từng phường được cách ly bằng PostgreSQL RLS; model/provider/key chỉ thuộc cấu hình Developer.

**Chưa sẵn sàng production.** Local mặc định dùng Mock có nhãn; không nhập hồ sơ công dân thật. Xem [trạng thái](docs/IMPLEMENTATION_STATUS.md), [test report](docs/TEST_REPORT.md), [điểm tiếp tục](docs/RESUME.md).

## Phạm vi và lộ trình hiện hành

Người dân hỏi đáp công khai, không đăng nhập. Admin quản lý tài liệu/tri thức và xuất bản. Không triển khai hồ sơ cá nhân, Actions/phản ánh/đặt lịch, voice/image/code/MCP, file công dân hoặc crawler trong v2.

Đích bàn giao còn gồm chất lượng AI thật, widget nhúng cổng khác origin, bảo mật Admin, giới hạn sử dụng/chi phí cơ bản, retention, kiểm thử tải, backup/restore và nghiệm thu. Widget hiện tại chỉ nhúng cùng origin; khác origin là việc P3 cần làm, chưa phải chức năng đã nghiệm thu.

- [Đặc tả v2](CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md).
- [Kế hoạch P0–P5 và 32 task](docs/IMPLEMENTATION_PLAN.md).
- [Bảng yêu cầu và 45 kịch bản nghiệm thu](docs/REQUIREMENTS_CHECKLIST.md).
- [Thay đổi phạm vi so với v1](docs/SCOPE_CHANGE_V2.md).

P1/W-01–W-09 đã triển khai và kiểm thử local: upload retry không tạo trùng, metadata/nguồn/phân loại, kho/lịch sử phân trang, review/diff, corpus thật và phục hồi/purge/orphan cleanup nền tảng. Xem [báo cáo P1](docs/P1_IMPLEMENTATION_REPORT.md) và [trích xuất corpus](docs/EXTRACTION_REPORT.md). P2–P5 còn các điều kiện chất lượng AI, nhúng và vận hành; P1 chưa phải phần mềm hoàn chỉnh.

## Chạy bằng Docker Desktop trên Windows

Cần Docker Desktop với Linux Engine đang chạy và PowerShell. Lần đầu cần internet tải image/dependency; MinIO được build từ source chính thức có checksum vì image public không còn tải được. Không cần cài Python/Node để chạy Compose; bootstrap có thể dùng image Python khi máy không có Python.

M2 thêm ClamAV và OCR; Compose dành tối đa 4 GB RAM cho ClamAV và 2 GB cho parser, ngoài các dịch vụ còn lại. Lần đầu ClamAV nạp signature có thể mất vài phút. File không được sử dụng nếu scanner chưa sẵn sàng.

```powershell
.\scripts\bootstrap.ps1
.\scripts\dev.ps1
.\scripts\check.ps1
```

Nếu Windows PowerShell báo chặn chạy script, có thể chạy từng script trong process riêng; không đổi ExecutionPolicy toàn máy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

- Cổng quản trị: http://localhost:8080/admin
- OpenAPI: http://localhost:8080/api/v1/openapi.json
- Hướng dẫn API: http://localhost:8080/api/v1/docs
- Readiness: http://localhost:8080/health/ready
- Tài khoản/mật khẩu cấp lần đầu: `.local/provisioned-admins.json` trên máy. Đăng nhập bắt buộc đổi mật khẩu. Không chia sẻ file này hoặc đưa vào Git.
- Trang công dân: từ nút **Mở trang công dân** sau đăng nhập; hoặc dùng `public_key` trong file local tại `/chat/{public_key}`. Widget cùng nguồn dùng `/embed/{public_key}` hoặc `/widget.js`.

Script chạy lại giữ nguyên `.env`, tài khoản, tri thức và volumes. Nếu port 8080 bị chiếm, đổi cả `APP_LOCAL_PORT` và `APP_PUBLIC_URL` trong `.env`. Script không tự dừng process khác. Các service nội bộ không có port public; gateway chỉ bind `127.0.0.1`.

## Linux Docker

```sh
bash scripts/bootstrap.sh
bash scripts/dev.sh
bash scripts/check.sh
```

Dockerfiles được build/chạy bằng Linux containers trong phiên phát triển. Luồng shell scripts trên máy Linux độc lập chưa được nghiệm thu; xem test report.

## Phát triển và browser tests

Cần Node.js 24, pnpm 12.18.0, Python 3.12, uv 0.13.7. Có thể dùng `npx --yes pnpm@12.18.0` nếu chưa cài pnpm. Không đặt AI secrets vào biến `NEXT_PUBLIC_*`.

```sh
uv sync --project apps/api
pnpm install --frozen-lockfile
pnpm generate:api
pnpm typecheck
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

E2E cần stack đang chạy. Test tạo các phường fixture riêng qua CLI; không sửa mật khẩu/nội dung phường mẫu người dùng. Credentials/trace/screenshot fixture chỉ ở `.local`, `test-results`, `playwright-report`, đều được bỏ qua bởi Git. Không công bố trace vì có thể chứa token test.

`check` và E2E yêu cầu `APP_ENV=local/test`, `AI_PROVIDER=mock`, `EMBEDDING_PROVIDER=disabled` và dừng trước khi chạy test nếu cấu hình khác. Không tự đổi cấu hình AI của bạn. Hướng dẫn upload/review: [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md).

## Cấu hình AI thật

Developer đặt `AI_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL` trong `.env` local/secret manager. Không có model mặc định và không tự chuyển Mock khi provider lỗi. Adapter dùng SDK chính thức/Responses API, `store=false`, structured output và kiểm tra evidence IDs phía backend. Cờ `store=false` không thay thế việc thẩm định retention của provider.

Chưa chạy live AI evaluation trong phiên khởi tạo. Không dùng pass của Mock để kết luận chất lượng AI thật. Nguồn chính thức: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

Embeddings mặc định `disabled`; local vẫn tìm theo từ khóa thật. Developer có thể cấu hình profile, reindex các nguồn đã duyệt công khai rồi dùng pgvector/hybrid; xem [OPERATIONS.md](docs/OPERATIONS.md). Không tự bật embeddings hay gửi tài liệu đến API ngoài.

## Dừng local

```sh
docker compose stop
```

Không dùng `down -v` khi muốn giữ dữ liệu. Không push Git, mở internet hoặc tạo tài nguyên tính phí trong quá trình bootstrap.

