# Báo cáo kiểm thử — P1 v2 và lịch sử M0–M2 local

## P1 v2 — ngày 13/11/2026

Phạm vi W-01–W-09, Windows PowerShell/Docker Desktop Linux Engine 29.9.2, PostgreSQL/pgvector/Redis/private MinIO/ClamAV/parser thật; AI Mock có nhãn, embeddings disabled. Không gọi paid API, không publish corpus nguồn thật, không dùng SQLite thay RLS. Source phần lớn vốn untracked; không reset/stage/push Git hoặc xóa volumes.

| Lệnh/kiểm tra | Kết quả thực chạy |
|---|---|
| Baseline `scripts/check.ps1` trước thay đổi | 56 backend passed (24,77s), Ruff/mypy và frontend build đạt |
| Baseline Chromium trước thay đổi | 6 passed (48,6s) |
| `scripts/check.ps1` sau thay đổi P1 | 64 passed, 1 skipped (35,67s); Ruff/mypy và frontend Docker production build đạt |
| Backend source cuối sau bổ sung data-policy guard/assertions, mount vào test image | 64 passed, 1 skipped (42,14s); corpus opt-in là test skipped, đã chạy riêng dưới đây |
| Ruff `src tests migrations`; mypy `src` | Pass; mypy 29 source files |
| Ruff hai script checklist/corpus | Pass |
| `python scripts/update_requirement_checklist.py` | Pass FR/NFR/W/AT, chỉ đọc và không suy pass |
| Corpus opt-in với PUBLIC_CORPUS_DIR/REPORT | 1 passed (94,30s); 22 originals + 1 derived scan; tổng case time 88,000s |
| `pnpm generate:api`, `pnpm typecheck` | Pass, schema TypeScript sinh lại từ OpenAPI |
| Frontend Docker production build cuối | Pass Next.js/TypeScript sau chỉnh nhãn metadata/diff và bỏ quảng bá tải original công khai |
| `pnpm test:e2e` bản cuối trên stack đã khởi động lại | **8 passed (49,4s), Chromium**, 6 regression M1/M2 + 2 luồng P1 |
| Migration 0004 `alembic upgrade head` | Pass trên DB hiện có; không reset dữ liệu |
| Stack readiness/worker/ingester ping | Pass local; readiness cuối trả ready |

Lệnh backend cuối (bind path thay theo workspace):

```powershell
docker compose run --rm --no-deps -v D:/Work/Project/AI_Chatbot/apps/api:/workspace -w /workspace -e PYTHONPATH=/workspace/src tests pytest -q -p no:cacheprovider
```

Corpus dùng lệnh opt-in trong [EXTRACTION_REPORT.md](EXTRACTION_REPORT.md). Manifest có 22 hash duy nhất: 9 PDF/8 DOCX/3 XLSX/2 HTML. 21 originals trích xuất; HTML JavaScript-only trả EXTRACTION_EMPTY đúng dự kiến, không tính là thành công. Tính ảnh dẫn xuất: 10 ready/12 needs_review/1 failed dự kiến; 508 trang PDF được parser báo đọc. Đây là bằng chứng kỹ thuật trên corpus khai báo, không phải kiểm chứng hiệu lực pháp lý hoặc AI/ngữ nghĩa.

Bổ sung backend gồm 6 integration cases trong test_p1 và 2 unit parser/format. Kiểm retry/concurrency/partial batch, payload conflict, RLS/FK của receipts, metadata strict/null/URL/classification/supersedes, 205 phiên bản/11 trang, lịch sử không body lớn, diff/immutable/review race, dry-run/grace/tenant boundary/linked objects, stale parser và process kill thật sau parser/S3 delete. Recovery fixture chủ động hết lease trong DB để tái lập nhanh, không phải fault test toàn broker/host. External Preview guard được kiểm bằng config giả lập/không paid request.

Browser mới kiểm tìm/phân trang kho và lựa chọn nháp qua nhiều trang, sửa metadata nguồn/tags/supersedes và diff nội dung. Artifact local: `.local/evidence/p1-catalog.png`, `p1-version-diff.png`, `.local/p1-e2e-final.log`, `test-results/.last-run.json` (passed), `playwright-report/index.html`. Không công bố credentials hoặc traces. Các luồng M1/M2 vẫn dùng fixture tenant mới riêng lượt chạy.

Trong quá trình làm có browser failures do selector cũ, request fixture thiếu Origin và lựa chọn phiên bản theo accessible name; đã sửa test theo hành vi UI mới, không nới CSRF. Lượt trước bản cuối bị gián đoạn khi toàn bộ Docker stack dừng, gây mất kết nối; sau khởi động lại, bản cuối đủ 8 pass. Không cộng các lượt lỗi thành bằng chứng pass.

Đầu ra/scope/giới hạn tại [P1_IMPLEMENTATION_REPORT.md](P1_IMPLEMENTATION_REPORT.md). P2 semantic/live/history/preflight, P3 khác origin, P4 MFA/budget/retention/load/security/restore, P5 UAT/pilot vẫn chưa nghiệm thu. Orphan cleanup là CLI batch tối đa 10.000 objects, chưa scheduler/checkpoint toàn kho; public source hiện excerpt, chưa tải original công khai. Production vẫn bị khóa. Không chuyển số test thành số AT hoàn tất toàn bộ.

## Lịch sử M0–M2 — giữ nguyên bằng chứng ngày 10/11/2026

Ngày chạy: **10/11/2026**, Asia/Ho_Chi_Minh. Windows PowerShell, Node 24.14.0/Python 3.12.10, Docker Desktop Linux Engine. PostgreSQL 17.8 + pgvector/Redis thật; toàn bộ nội dung là dữ liệu giả, AI là Mock.

## Bổ sung M2

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1` bản cuối **pass**: Ruff (src/tests/migrations), mypy, **56 backend tests** (35 unit + 21 integration) và frontend Docker production build. Trước đó 55 tests pass; bổ sung test giữ table context và hàng nguyên vẹn đưa tổng lên 56. `pnpm generate:api` và `pnpm typecheck` cũng đã chạy đạt.

6 Chromium E2E M1/M2 pass: luồng M1 vẫn có Preview/public isolation, publish/chat/source/feedback, model-field rejection, mobile chat và widget; thêm upload CSV → ClamAV/worker thật → metadata/review → Preview với dòng nguồn → file version 2, và Excel hidden-sheet/formula warnings → review → purge hoàn tất. Artifact `.local/evidence/m2-upload-version.png`, `m2-extraction-review.png`; HTML report `playwright-report/index.html`. Không công bố trace/credentials.

M2 backend fixtures thật kiểm tra PDF 2 trang, scan tiếng Việt/PDFium+Tesseract, PNG/JPG OCR, DOCX headings/table/header không số trang giả, XLSX merged/formula cached value/hidden sheet, PPTX slides, TXT/MD/CSV/HTML. Kiểm tra MIME/magic/size/archive bomb/XML entity, parser subprocess limits, scanner mất kết nối fail closed và ClamAV phát hiện chuỗi EICAR trong bộ nhớ.

Ba trường hợp PDF scan/PNG/JPG còn được chạy lại trong chính subprocess parser với giới hạn CPU/RAM và environment sạch: **3 passed**, không gọi OCR API bên ngoài. Đây là tăng mức kiểm tra cho 3 test có sẵn trong tổng 56, không cộng trùng thành 59. `scripts/dev.ps1` bản cuối đạt readiness/worker ping; E2E cuối sau thay đổi table chunk: **6 passed (43.1s)**.

Integration dùng MinIO thật/private anonymous 403; API truy cập file/job/version/source chéo tenant bị chặn; worker idempotency, review revision/section ownership, metadata strict fields/ngày hiệu lực/published immutable, file version giữ nguyên bản cũ, original download sạch, thu hồi trước purge, xóa object/chunks/vectors/sections/review/derived answer và chặn worker cũ hồi sinh. pgvector test tạo/lưu/query vector thật, trigger dimension, profile mismatch, global catalog runtime không ghi được, RLS và filtered hybrid. Vector/SDK fixtures không chứng minh chất lượng tìm ngữ nghĩa.

Lỗi phát hiện khi chạy lại và đã sửa: fixture embedding fingerprint bị trùng giữa các lần chạy; fixture manifest E2E tích lũy tenant cũ khiến browser chọn dữ liệu đã publish của lần trước. Manifest E2E hiện chỉ chứa tenant mới của chính lượt chạy, không sửa tài khoản/dữ liệu phường mẫu. Không có lỗi draft leak trong DB snapshot ở trường hợp đó.

Chưa nghiệm thu: live OpenAI/semantic benchmark tiếng Việt, corpus nghiệp vụ/layout phức tạp, hard worker kill/load/concurrent race/fuzz toàn diện, quota/pricing embeddings, orphan sweeper, backup/provider deletion/restore, Linux host scripts và các chức năng M3–M8. M2 vẫn **in_progress** trong status.

## Bằng chứng nền tảng M0–M1 (giữ lịch sử)

| Lệnh/kiểm tra đã chạy | Kết quả cuối |
|---|---|
| `scripts/bootstrap.ps1` | Pass: env/migration/seed hai phường/private bucket |
| `scripts/dev.ps1` | Pass toàn bộ phiên bản cuối: gateway readiness, worker ping trả pong và scheduler đang chạy |
| `scripts/verify_bootstrap.py before`, bootstrap lần hai, `after` | Pass: hash .env/credentials và số account/document/release của cả hai phường không thay đổi |
| `scripts/check.ps1` | Pass: Compose config, Ruff, mypy, pytest và Docker web build |
| `docker compose run --rm tests` trong check script | **33 passed in 5.61s** |
| `mypy src` trong test container | Pass: no issues, 16 source files |
| `ruff check --no-cache src tests migrations` | Pass |
| `pnpm generate:api` | Pass: TypeScript schema sinh từ OpenAPI thật |
| `pnpm typecheck` và `pnpm build` | Pass: frontend/widget strict TypeScript, Next.js build |
| `pnpm test:e2e` | **4 passed in 21.3s**, Chromium |
| Bootstrap guard với Docker command failure stub trong process riêng | Pass: dừng sớm với hướng dẫn Engine; không tắt Docker thật |
| PowerShell UTF-8 BOM, Git ignore boundaries, `git diff --check` | Pass; .env/credentials/.local không thuộc candidate source |
| Docker source builds | API/web/MinIO pass; source/image versions và digests được khóa |

## Nội dung thực sự được kiểm thử

19 unit/adapter cases và 14 integration cases: runtime role không superuser/BYPASSRLS, default-deny khi thiếu tenant, pool không giữ context, RLS/composite FK chống đọc/ghi chéo, DTO model injection/CSRF, public/draft isolation, source ownership, publish/rollback/revision/hash, idempotency/single active turn, SSE replay/feedback, nguồn bị thu hồi khi generate, result/source/SSE cũ được chặn sau thu hồi, Preview mất quyền sau Admin logout.

4 E2E với worker/scheduler/broker thật:

1. Admin A login/đổi mật khẩu → nhập tri thức → xác nhận công khai → lưu nháp → Preview → kiểm tra public chưa thấy draft → validate/publish → chat có nguồn → feedback; phường B không thấy nội dung A.
2. Admin API từ chối model injection; UI không có tenant/model selector.
3. Chat mobile 390×844 không tràn ngang và mở được nguồn.
4. Widget cùng nguồn mở iframe, trả lời có nguồn và đóng được.

Artifacts thật: `.local/evidence/admin-published.png`, `chat-with-source.png`, `mobile-chat.png`; browser HTML report tại `playwright-report/index.html`. Fixture credentials/trace bỏ qua bởi Git; không công bố trace hoặc secret. Coverage theo từng T-ID ở `REQUIREMENTS_CHECKLIST.md`, không phải 70 kịch bản đã pass.

## Những lỗi đã phát hiện và sửa

- DDL format('%I') qua SQLAlchemy empty parameters: dùng DBAPI cursor cho static DDL trong cùng Alembic transaction.
- CLI dùng migration owner bỏ qua RLS: transaction có tenant hạ về runtime role; composite FK chặn dữ liệu sai trước commit.
- PowerShell 5.1 cần UTF-8 BOM; khi execution policy chặn, chỉ dùng override process như README, không đổi policy máy.
- Worker no-dev thiếu packaging của Kombu Redis: đưa vào runtime dependencies và thêm worker healthcheck/ping.
- Nginx cache IP upstream cũ sau recreate: dùng Docker DNS resolver động.
- TypeScript 7 cần module/rootDir phù hợp cho widget; E2E selectors khớp accessible labels thực tế.

## Chưa chạy/giới hạn

Live OpenAI evaluation và API nghiệp vụ/IdP thật: **not_run / blocked_external_dependency**. Adapter OpenAI chỉ contract test giả lập SDK; không có paid call trong phiên này. OCR/files đã kiểm thử như phần M2 phía trên; semantic quality/crawler/Actions/voice/images/load/soak/security scan/restore/trình duyệt khác/accessibility đầy đủ chưa nghiệm thu. Linux Dockerfiles chạy thật qua Docker Desktop; Linux host shell scripts chưa nghiệm thu độc lập.

Không có kết luận production ready, SLA, tuân thủ pháp lý hoặc độ chính xác nghiệp vụ 95% từ bộ test này. Production vẫn bị chặn trong Settings.
