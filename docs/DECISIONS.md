# Quyết định sản phẩm và kỹ thuật

## Quyết định v2 ngày 13/11/2026

| ID | Quyết định | Lý do / hệ quả |
|---|---|---|
| ADR-201 | Q&A công khai, đa đơn vị, không citizen auth/Actions | Khớp nhu cầu người dùng; bỏ IdP/API hồ sơ và nghiệp vụ ghi khỏi điều kiện nghiệm thu |
| ADR-202 | Admin upload/nhập thủ công; không crawler/web search | Giảm phạm vi; vẫn lưu source URL/hash và review nguồn, không tự fetch URL từ API |
| ADR-203 | Giữ stack và dữ liệu hiện có, migration tiến | Tận dụng M0–M2; chưa viết lại hoặc nâng dependency trong lượt tài liệu |
| ADR-204 | Widget iframe khác origin, API cùng origin chatbot | Không phụ thuộc cookie/SSO cổng; cần exact-origin/frame-ancestors/trust postMessage và browser tests |
| ADR-205 | Một Admin active/tenant, MFA production, CLI provision | Admin cơ bản vẫn cần bảo vệ kho nội dung; không cần platform Admin portal lớn |
| ADR-206 | Lexical+pgvector/RRF; tách query embedding khỏi transaction | Giữ quyền/revocation; sửa pool/latency trước đo tải, chất lượng phải đo live |
| ADR-207 | Usage/budget/rate/retention tối thiểu, không BI lớn | Chat public vẫn có rủi ro lạm dụng và chi phí; atomic reserve/unknown reconcile cần test |
| ADR-208 | Evaluation CLI/report, public corpus có nhãn/nguồn | Đủ truy vết chất lượng mà không cần dashboard lớn; human review trước UAT |
| ADR-209 | Single-host Linux Docker, RPO24h/RTO4h làm mục tiêu | Chưa có nhu cầu HA/PITR được xác nhận; khác mục tiêu RPO1h đề xuất v1, phải đo restore |
| ADR-210 | P0–P5/G0–G5/FR-NFR-AT là mã hiện hành | Tránh đổi nghĩa milestone/test ID lịch sử; M4/M5 không bị coi còn thiếu |
| ADR-211 | Production guard chỉ chuyển khi G4 đạt | Không xóa validator APP_ENV chỉ để chạy public; giữ Mock/secret/RLS/MFA/budget/policy gates |
| ADR-212 | P0 chỉ tài liệu; không chạy baseline test hay sửa generator v1 | Tôn trọng yêu cầu trước code; W-01/W-02 bắt đầu ở lượt code được yêu cầu sau |

Mặc định tải/retention/chất lượng là phương án lập kế hoạch, chưa phải kết quả, SLA hoặc sự phê duyệt của đơn vị. Chi tiết thay đổi: SCOPE_CHANGE_V2.md. Domain/model/hạ tầng cụ thể cần được cấp khi bước tiếp theo phụ thuộc.

## Quyết định v1 giữ làm lịch sử

Các ghi chú dưới đây thuộc các lượt M0–M2 trước, không làm sống lại yêu cầu Actions/capabilities/crawler. Khi nói không giữ transaction qua AI, cần nhớ code query embedding còn một khoảng trống đã ghi trong ARCHITECTURE và W-10.

- Giữ baseline Next.js/TypeScript, FastAPI/Python 3.12, PostgreSQL 17/pgvector, Celery/Redis và Docker.
- M1 dùng lexical retrieval PostgreSQL thật. Hybrid vectors thuộc M2, không dùng mock embeddings để kết luận chất lượng retrieval.
- Runtime và migration dùng tài khoản database riêng. Directory đăng nhập/public chỉ chứa định danh tối thiểu; dữ liệu nghiệp vụ có RLS và composite foreign keys.
- M1 chỉ nhận tri thức văn bản có giới hạn, có public approval tường minh; không giả chức năng upload/OCR hoặc Actions.
- Lưu turn/event/outbox trong PostgreSQL, stream chỉ phát answer đã kiểm tra. Không giữ transaction mở khi gọi AI.
- Production bị khóa cho đến khi các kiểm soát còn thiếu và go-live gates thực sự đạt.
- MinIO local build từ source chính thức release `RELEASE.2025-10-15T17-29-55Z`, commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`, archive SHA256 `45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841`: Docker Hub trả pull denied, Quay trả 401 trong phiên này. Repository upstream đã archive ngày 25/04/2026. Giữ MinIO chỉ cho local theo baseline; phải review security/license/nhà cung cấp storage được duy trì trước production. Nguồn: https://github.com/minio/minio ; https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z .

