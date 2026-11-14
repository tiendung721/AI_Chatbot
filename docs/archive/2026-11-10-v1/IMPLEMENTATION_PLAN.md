# Kế hoạch triển khai

Baseline: đặc tả v1.0 ngày 10/11/2026. Phát triển theo lát cắt xuyên UI/API/database/worker.

| Milestone | Phạm vi | Điều kiện hoàn thành |
|---|---|---|
| M0 | Monorepo, Docker, migrations, RLS, CLI, auth, adapters | Runtime role kiểm thử bằng PostgreSQL thật, startup fail closed |
| M1 | Văn bản → nháp → kiểm tra → publish → chat có nguồn → feedback | E2E hai tenant, draft isolation, rollback, model injection bị chặn |
| M2 | File, OCR, scanning, vectors, hybrid RAG, purge | Fixture thật, locator/coverage và quyền được kiểm thử |
| M3 | Website sync, Builder đầy đủ, evaluation/release | SSRF/diff/hash/concurrency tests |
| M4 | OIDC và Actions | Ownership/confirmation/idempotency/reconciliation |
| M5 | Web/attachments/code/images/voice/extensions | Adapter contracts, trạng thái cấu hình và live smoke được tách riêng |
| M6 | Usage/quota/audit/retention | Atomic budget và đối soát |
| M7 | Hardening/CI/deploy/backup | Security/load/restore có bằng chứng |
| M8 | Tích hợp thật/UAT | Đủ đầu vào và go-live gates, đơn vị nghiệm thu |

Ưu tiên hiện tại: M0 → M1. Không thu hẹp phạm vi cuối; M2–M8 tiếp tục theo thứ tự.
