# Phiên bản và nguồn kiểm tra

Đối chiếu registry chính thức ngày 10/11/2026; exact direct dependencies ở package manifests, transitive/integrity ở `pnpm-lock.yaml` và `apps/api/uv.lock`. Không dùng model ID mặc định hoặc giá suy đoán.

| Thành phần | Phiên bản đã chọn |
|---|---|
| Node.js | 24.14.0, image bookworm-slim có digest |
| pnpm | 12.18.0 |
| Next.js / React | 16.4.6 / 19.3.1 |
| TypeScript | 7.0.2, strict |
| Playwright | 1.65.0, Chromium đã cài cho test |
| Python / uv | 3.12.10 / 0.13.7 |
| FastAPI / Pydantic | 0.162.2 / 2.14.3 |
| SQLAlchemy / Alembic / psycopg | 2.1.8 / 1.20.1 / 3.3.8 |
| Celery / Redis Python | 5.7.0 / 8.1.0 |
| OpenAI SDK | 3.49.0 |
| pgvector image | 0.8.1-pg17, digest cố định; runtime PostgreSQL 17.8 |
| Redis server / Nginx | 8.0.2-alpine / 1.28.0-alpine, digest cố định |
| MinIO local | Source release 2025-10-15, commit/checksum tại Dockerfile |
| ClamAV | 1.5.4-debian13-slim, full image kèm signature, khóa digest trong Compose |
| OCR | Tesseract 5.3.0 từ Debian bookworm; vie + eng; có font DejaVu trong parser/test image |
| PDF | pypdf 7.0.1 / pypdfium2 5.15.2 |
| Office | python-docx 1.2.0 / openpyxl 3.1.5 / python-pptx 1.0.2 |
| Ảnh / HTML / XML | Pillow 13.0.0 / beautifulsoup4 4.15.0 / defusedxml 0.7.1 |
| Fixtures PDF | reportlab 5.1.0, chỉ dependency test |

`packaging==26.3` là dependency runtime tường minh vì Kombu Redis transport cần import này; không dựa vào pytest/dev dependencies để worker chạy. TypeScript 7 không hỗ trợ module=none; widget dùng esnext, rootDir rõ, output vẫn là script IIFE không imports/exports.

Nguồn: https://registry.npmjs.org/ ; https://pypi.org/ ; https://www.postgresql.org/docs/17/ddl-rowsecurity.html ; https://docs.sqlalchemy.org/en/20/orm/session_transaction.html ; https://nextjs.org/docs/app/getting-started/installation ; https://developers.openai.com/api/docs/guides/structured-outputs . API key không cần để đọc docs và chạy Mock tests.

Kiểm tra license/CVE production chưa hoàn tất. MinIO dùng AGPL-3.0; giữ LICENSE trong image, source chính thức có commit cố định tại https://github.com/minio/minio . Không coi việc khóa phiên bản là bằng chứng đã qua security scan. pnpm tự thêm minimumReleaseAgeExclude theo exact phiên bản Next đã lấy từ registry; danh sách đó ở workspace config, không dùng wildcard.
