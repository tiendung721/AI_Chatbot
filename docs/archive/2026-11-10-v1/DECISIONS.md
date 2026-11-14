# Quyết định kỹ thuật

- Giữ baseline Next.js/TypeScript, FastAPI/Python 3.12, PostgreSQL 17/pgvector, Celery/Redis và Docker.
- M1 dùng lexical retrieval PostgreSQL thật. Hybrid vectors thuộc M2, không dùng mock embeddings để kết luận chất lượng retrieval.
- Runtime và migration dùng tài khoản database riêng. Directory đăng nhập/public chỉ chứa định danh tối thiểu; dữ liệu nghiệp vụ có RLS và composite foreign keys.
- M1 chỉ nhận tri thức văn bản có giới hạn, có public approval tường minh; không giả chức năng upload/OCR hoặc Actions.
- Lưu turn/event/outbox trong PostgreSQL, stream chỉ phát answer đã kiểm tra. Không giữ transaction mở khi gọi AI.
- Production bị khóa cho đến khi các kiểm soát còn thiếu và go-live gates thực sự đạt.
- MinIO local build từ source chính thức release `RELEASE.2025-10-15T17-29-55Z`, commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`, archive SHA256 `45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841`: Docker Hub trả pull denied, Quay trả 401 trong phiên này. Repository upstream đã archive ngày 25/04/2026. Giữ MinIO chỉ cho local theo baseline; phải review security/license/nhà cung cấp storage được duy trì trước production. Nguồn: https://github.com/minio/minio ; https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z .
