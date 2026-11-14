# Vận hành local hiện có — phạm vi v2

Đặc tả hiện hành là v2.0/P0–P5. Các lệnh dưới mô tả code local sau P1; chưa nghiệm thu production và không tự cấp quyền gọi paid API. Đăng nhập công dân/Actions/crawler ngoài scope.

```sh
docker compose ps --all
docker compose logs --tail 100 api worker scheduler web nginx
docker compose logs --tail 100 ingester parser clamav
docker compose exec -T worker celery -A citizen_ai.workers:celery inspect ping --timeout 5
docker compose run --rm ops python -m citizen_ai.cli ops validate-runtime
```

Logs ứng dụng chỉ ghi request/turn IDs, mã lỗi và loại exception; không chủ động ghi nội dung công dân, token hoặc raw provider response. Không công bố `.env`, credentials hoặc trace E2E. OpenAI timeout/429 dùng SDK retry hữu hạn; không chuyển Mock để che lỗi.

## Tài liệu sai hoặc chatbot cần dừng

Admin thu hồi văn bản trong Kho tri thức hoặc tạm dừng ở Tổng quan. Thu hồi được kiểm tra trước khi phát hành câu trả lời và khi đọc lại nguồn/result/SSE. Rollback không khôi phục nguồn đã thu hồi. Đây không phải purge bytes hoặc xóa khỏi backup.

## Cấp và bàn giao Admin

```sh
docker compose run --rm ops python -m citizen_ai.cli ops create-tenant --slug ward-new --name "Don vi moi"
docker compose run --rm ops python -m citizen_ai.cli ops provision-admin --tenant ward-new --email new@example.invalid
docker compose run --rm ops python -m citizen_ai.cli ops rotate-admin --tenant ward-new --email replacement@example.invalid
```

Mật khẩu nhập qua prompt, không qua tham số command line. Bàn giao vô hiệu người cũ, thu hồi phiên, ghi audit; Preview của phiên Admin cũ cũng mất hiệu lực. Không dùng tài khoản dùng chung. Không có route public cho CLI hoặc model settings.

## Worker/stream lỗi

Kiểm tra health worker/scheduler và queue. Outbox lưu trong PostgreSQL, dispatcher phát lại turn chưa hoàn tất sau khoảng chờ; worker có lease và fencing token, không commit đè kết quả của worker mới. GET terminal result phục hồi khi mất stream; cùng client_request_id không tạo lại turn. Actions và connector nghiệp vụ ngoài phạm vi v2; luồng hiện tại chỉ tạo câu trả lời hỏi đáp.

## Backup/restore và sự cố production

Chưa triển khai/đo restore drill, PITR, monitoring alerts hoặc HA. Cần backup DB + objects + config, keys phục hồi riêng, retention/deletion ledger và kiểm tra sau restore ở P4/G4. RPO/RTO trong đặc tả là mục tiêu đề xuất chưa được đo. Không dùng redirect nhị phân PowerShell 5.1 để giả lập bằng chứng backup. Không chạy drop/reset/down -v để khắc phục sự cố local.

## File Knowledge và embeddings

`ingester` chỉ nhận queue `ingestion`; worker chat nhận queue mặc định. Scheduler dispatch theo outbox; scanner lỗi phải fail closed, không đặt `scan_status=clean`. Parser chạy trên network `parsing` internal, không có DB/key, filesystem read-only và subprocess có giới hạn tài nguyên. Chỉ ingester có đường truyền file sang parser. ClamAV có signature thật và volume riêng; không publish port parser/ClamAV/MinIO.

`EMBEDDING_PROVIDER=disabled` là mặc định. Khi đã có quyền gửi nguồn ra provider, Developer đặt `EMBEDDING_PROVIDER=openai`, `OPENAI_EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `EMBEDDING_PROFILE_ID` (UUID) và key ở backend. Adapter gửi tham số `dimensions`; model phải hỗ trợ tham số này. Không có model/dimension suy đoán. Nguồn API: [Create embeddings](https://developers.openai.com/api/reference/resources/embeddings/methods/create).

```sh
docker compose run --rm ops python -m citizen_ai.cli ops create-embedding-profile
docker compose run --rm ops python -m citizen_ai.cli ops reindex-knowledge --tenant ward-new
```

Tạo profile không gọi provider; **reindex có thể tính phí và gửi nội dung chunks đã duyệt công khai ra provider**. Lệnh có checkpoint theo chunk/profile, chạy lại không tạo vector trùng. Không chạy các lệnh này chỉ để thử UI. Query embedding cũng gửi câu hỏi tới provider khi bật cấu hình.

Đổi dimension/model/chunker cần UUID/profile khác, build index song song bằng cấu hình riêng cho lệnh ops, đánh giá trước khi chuyển cấu hình API/worker và xuất bản lại. Runtime kiểm tra fingerprint/dimension; publish bị chặn nếu nguồn thiếu vector. Không xóa hoặc cập nhật profile cũ. Exact cosine search lọc tenant/profile/release/quyền/hiệu lực/thu hồi trước khi xếp hạng, sau đó hợp nhất lexical/vector bằng RRF. Semantic evaluation tiếng Việt/live AI chưa chạy. Mock embedding chỉ là fixture kiểm tra đường đi dữ liệu.

Purge hiện xử lý kho đang hoạt động; không tuyên bố đã xóa backup hoặc bản lưu provider. Backup/restore, resource tuning, quota/giá embedding và security scan thuộc P4.

## Đối soát orphan objects — P1

Operator chạy theo đúng tenant slug; mặc định chỉ xem trước, không xóa:

```sh
docker compose run --rm ops python -m citizen_ai.cli ops sweep-orphans --tenant TENANT_SLUG
```

Đọc kết quả counts/audit và xác nhận tenant/grace phù hợp trước khi thêm `--apply`. Có thể đặt `--grace-hours 48` và `--maximum 1000`; grace tối thiểu 24 giờ, maximum tối đa 10.000 objects. Chỉ xử lý key original có cấu trúc UUID trong prefix tenant, quá grace, không còn tham chiếu DB; đối chiếu ETag/size/cutoff lần cuối và khóa với upload. Không xóa object đang được version trỏ tới hoặc bucket ngoài tenant.

Đây là CLI theo batch, chưa có scheduler/checkpoint để quét toàn kho lớn hay retention tự động. Nếu có hơn giới hạn object cần giải pháp quét tiếp ở P4; không tăng số bằng cách bỏ giới hạn an toàn. Sau unknown DB COMMIT, giữ object chờ đối soát; không tự xóa file chỉ vì POST lỗi. Purge còn xóa filename của upload receipt; receipt purged không được dùng phục hồi nội dung.

Corpus kỹ thuật P1 và cách tái lập tại [EXTRACTION_REPORT.md](EXTRACTION_REPORT.md). Collector chỉ tải catalog nguồn cố định cho test, không phải crawler của sản phẩm; không tự publish hoặc gọi embeddings/AI thật. Không dùng corpus lịch sử/chưa hiệu lực làm câu trả lời hiện hành nếu chưa được reviewer kiểm tra.

