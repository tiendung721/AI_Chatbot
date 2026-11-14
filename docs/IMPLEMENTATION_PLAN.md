# Kế hoạch triển khai v2.0 — chatbot hỏi đáp công khai

Ngày lập: 13/11/2026. Căn cứ: [master spec v2.0](../CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md).
Tài liệu này giữ kế hoạch được lập trong P0 trước code. Sau đó người dùng đã yêu cầu triển khai P1/W-01–W-09; kết quả local tại [báo cáo P1](P1_IMPLEMENTATION_REPORT.md) và [trạng thái](IMPLEMENTATION_STATUS.md). Các bảng dưới là tiêu chí kế hoạch, không tự chứng minh đã hoàn tất.

## 1. Phương án đã chọn

- Tận dụng Next.js/FastAPI/PostgreSQL RLS/pgvector/Celery/private storage và parser/OCR hiện có.
- Hoàn thiện hỏi đáp dựa trên tài liệu công khai đã duyệt; giữ một Admin/tenant và session ẩn danh cho người dân.
- Nhúng iframe từ origin chatbot vào các cổng khác origin; không dùng cookie/SSO của cổng.
- Bỏ OIDC công dân, Actions, API hồ sơ, voice/image/code/MCP, file công dân và crawler khỏi bản bàn giao v2.
- Giữ phần tối thiểu cần vận hành: MFA Admin, rate/concurrency/budget, retention, metrics, backup/restore và deployment.
- Dùng single-host Docker làm baseline. Model/key/storage production/domain/hạ tầng cụ thể chọn khi đến bước cần, không tự mua/tạo tài nguyên.

## 2. Hiện trạng được dùng để lập kế hoạch

| Đã thấy trong code | Khoảng trống cần giải quyết |
|---|---|
| RLS/composite FK, session Admin, DTO strict | Mở rộng test cho mọi schema mới; MFA/recovery/session UI chưa đủ |
| Text/upload/ClamAV/parser/OCR/review/version/purge | Metadata/phân trang/diff, request-id upload, hard-crash/race/corpus phức tạp, orphan/restore chưa đủ |
| Lexical + exact cosine/RRF/profile | Live semantic evaluation chưa có; query embedding đang nằm trong transaction retrieval |
| Draft/validate/publish/rollback/Preview | Preflight/evaluation gắn hash, diff và runtime revalidation cần hoàn thiện |
| Answer/evidence/source/SSE/feedback | Live quality, câu hỏi tiếp nối, nguồn mâu thuẫn và runtime lỗi cần kiểm chứng thêm |
| Loader/iframe cùng origin | widget.ts chặn origin khác; CSP/domain/mobile thật chưa nghiệm thu |
| Usage token events cơ bản | Chưa atomic budget/pricing/embedding accounting/unknown reconcile |
| Docker/scripts local | Production bị khóa vô điều kiện; chưa production package/load/security/restore/UAT |

Bằng chứng lịch sử: TEST_REPORT.md ngày 10/11/2026, 56 backend + 6 Chromium với Mock. Không chạy lại trong P0; không coi là pass cho yêu cầu mới. Source phần lớn còn untracked, phải giữ nguyên, không reset Git.

## 3. Giai đoạn và cổng ra

| Phase | Đầu ra | Điều kiện kết thúc |
|---|---|---|
| P0 — tài liệu | Spec v2, plan, checklist, status/resume/dependencies, scope mapping, archive v1 | G0 được rà soát; người dùng có bộ phương án cụ thể để xem trước code |
| P1 — tri thức | File/text/review/metadata/version/purge và worker ổn định; regression hai tenant | Các AT P1 đạt local; không gọi P1 là sản phẩm vận hành |
| P2 — hỏi đáp/AI/Admin | Answer/source/history/eval/preflight + Admin tối thiểu | G1; phần live của G2 chỉ đạt khi model/corpus/reviewer sẵn sàng |
| P3 — widget | Hai origin, domain/CSP/postMessage/mobile, hướng dẫn tích hợp | G3 với origin mô phỏng; cổng thật thuộc P5 |
| P4 — vận hành | MFA, giới hạn/chi phí, privacy/retention, load, backup, production package | G4 có evidence; AI quality còn thiếu vẫn chặn pilot public |
| P5 — UAT | Domain thật, corpus duyệt, live evaluation, tích hợp/pilot và bàn giao | G0–G5 đạt, không còn lỗi chặn hoặc đầu vào bắt buộc chưa được duyệt |

P1 hoàn thiện phần lớn M2 cũ. P2 lấy phần cần thiết của M3. M4/M5 cũ out_of_scope; M6/M7 giữ phần vận hành; M8 được rút về nghiệm thu hỏi đáp công khai. Không cần làm tuần tự đủ M0–M8 cũ.

## 4. Thứ tự và phụ thuộc

P0 → baseline code/checklist tooling → P1 → P2 core → P3 → P4 → P5.
Thu thập corpus có thể bắt đầu sau P0; budget/privacy ở P4 phải sẵn sàng trước live evaluation quy mô lớn. Live smoke nhỏ ở P2 chỉ thực hiện sau khi có cấu hình/key/giới hạn chi phí được cấp rõ.

P2 live evaluation có thể tạm chờ mà P3/P4 local vẫn tiếp tục. Không chờ domain thật để kiểm thử hai origin; không chờ IdP/API hồ sơ vì đã ngoài phạm vi. Code ngoài task quan trọng chỉ làm nếu lỗi mới cản tiêu chí hiện tại.

Các package dưới đây không phải mỗi package một commit bắt buộc; chia changeset nhỏ theo migration/service/UI/test, giữ các mốc có thể kiểm tra lại.

## 5. Backlog triển khai chi tiết

### P0 / chuyển tiếp sang code

| Task | Việc phải làm | Đầu ra và cách kiểm tra | Phụ thuộc |
|---|---|---|---|
| W-01 | Đối chiếu Git/current source; ghi baseline nonsecret; sửa công cụ sinh checklist v1 đang hardcode 70 T-ID | Tool không ghi đè checklist v2/không tự suy pass; giữ T-ID lịch sử. Đọc source scripts/update_requirement_checklist.py trước sửa | P0 |
| W-02 | Chạy baseline local khi bắt đầu code: check/typecheck/E2E; ghi command/môi trường/lỗi hiện có | Báo cáo mới riêng ngày chạy, phân biệt lỗi môi trường và lỗi sản phẩm; không chỉnh secrets/live config để test pass | W-01, Docker local |

W-01/W-02 đã thực hiện trong lượt code P1: validator chỉ đọc và baseline 56 backend/6 Chromium đạt. W-03–W-09 có triển khai và bằng chứng local trong báo cáo P1; các giới hạn live/production/UAT vẫn giữ nguyên.

### P1 / tri thức và vòng đời

| Task | Việc phải làm | Khu vực chính / tiêu chí ra | Phụ thuộc |
|---|---|---|---|
| W-03 | Corpus manifest: >=20 nguồn có hash/provenance/phạm vi, hai tenant, fixture được gắn nhãn | Corpus/evaluation data, không tải theo URL không kiểm soát; không tự publish. AT-09/22 | W-02 |
| W-04 | Bổ sung metadata/source/jurisdiction/tags/supersedes và quyền public-download khi thiếu | migrations, ingestion/models.py/router.py/content.py; FK/RLS/strict schema, dates/null, migration giữ dữ liệu. AT-01/08/09/12 | W-02 |
| W-05 | Batch upload idempotency theo client_request_id/fingerprint; retry từng file/đối soát object | ingestion/pipeline.py/router.py/storage.py; retry POST timeout không nhân version/job/object, payload khác conflict. AT-05/10 | W-04 |
| W-06 | Đánh giá trích xuất trên public corpus và fixture; sửa lỗi layout/OCR/table thực sự phát hiện | ingestion/parsers.py/formats.py/parse_job.py; coverage từng trang/sheet, giữ header/unit, báo lỗi tài liệu vượt khả năng. AT-06/07/08 | W-03/05 |
| W-07 | Job lease/fencing/retry/crash và review/revoke/purge concurrency | pipeline/workers/purge; kill process thật ở ít nhất parse và purge, worker cũ không hồi sinh data. AT-10/11 | W-05 |
| W-08 | Kho tìm/lọc/phân trang, chi tiết/review/diff/version; loading/error/empty/retry thật | main.py, web admin/knowledge-files; >200 versions vẫn truy cập được; stale revision conflict. AT-08/12 | W-04/06 |
| W-09 | Purge/retention foundations và orphan manifest/dry-run/grace period | storage/purge/CLI/jobs; không xóa active upload; derived result/source chặn sau revoke. AT-15/16/17 | W-04/07 |

Gate P1: unit/integration/PostgreSQL/E2E các thay đổi đạt, regression M1/M2 giữ được; corpus extraction report công bố phần thất bại, không giấu file khó. Chưa có live semantic benchmark không bị đổi thành passed.

### P2 / hỏi đáp, đánh giá và Admin

| Task | Việc phải làm | Khu vực chính / tiêu chí ra | Phụ thuộc |
|---|---|---|---|
| W-10 | Tách query embedding khỏi DB transaction; recheck release/profile/security epoch, timeout/cache scope | retrieval.py/ai/embeddings.py/chat.py; không giữ pool khi provider chậm; deny revoked/profile mismatch. AT-18/19 | W-04/07 |
| W-11 | Đánh giá lexical/hybrid và tuning có dữ liệu; sửa ranking/chunk theo lỗi thực | retrieval/ingestion; dataset có expected evidence, báo recall@8 và mẫu lỗi; không thay exact cosine bằng ANN khi chưa có nhu cầu. AT-18/22 | W-03/06/10 |
| W-12 | Q&A tiếng Việt, bounded history, clarify/no-source/conflict/out-of-scope; không nhận dạng hồ sơ cá nhân | chat.py/ai/contracts/adapters/schemas/web chat; history same session, câu cũ không được làm evidence. AT-20/21/23 | W-10/11 |
| W-13 | Validation output/source viewer/current revocation; UX result/SSE/cancel/retry | chat/common/main/web; source ID/locator đúng, replay/result không rò sau revoke, không nhân turn/cost. AT-15/19/24/25 | W-12 |
| W-14 | Bộ evaluation >=50 ban đầu, tiến tới >=200/holdout/rubric; runner/CLI/report và live opt-in có cap | evaluations/fixtures/CLI; fingerprint gắn mọi run, chấm người, report usage/error/latency riêng. AT-22/23/26 | W-03/11/12; live cần đầu vào E-02/03/04 |
| W-15 | Hoàn thiện config/đầu mối/dashboard/feedback cơ bản, che dữ liệu; ẩn năng lực ngoài phạm vi | web admin/main/schemas; counts từ DB, model injection reject, không menu model/citizen login/actions. AT-03/04/27 | W-08/12 |
| W-16 | Preflight/hash/evaluation gắn draft, diff/publish/rollback/runtime revalidation | content/main/migrations/UI; validation 30 phút, stale/runtime đổi bị chặn, revoke thắng history. AT-13/14/15/26 | W-08/14/15 |

Gate P2: G1 đạt local; G2 cần live AI/corpus/reviewer. Nếu chưa có key, kết thúc phần code và ghi blocked_external_dependency cho live, không dùng Mock để tuyên bố đạt 95%.

### P3 / nhúng cổng thông tin

| Task | Việc phải làm | Khu vực chính / tiêu chí ra | Phụ thuộc |
|---|---|---|---|
| W-17 | Tenant exact-origin allowlist, CLI cấp/thu hồi, policy CSP trên HTML embed và Admin | migrations/CLI/web/gateway; header theo tenant, Admin không bị frame, domain đổi có audit. AT-28/29 | W-04/15 |
| W-18 | Loader bỏ same-origin restriction theo policy; iframe source đúng, safe resize/close và fallback chat | widget.ts/web embed; origin/source/schema postMessage, token trong iframe memory, không gửi qua parent/URL. AT-28/30 | W-17 |
| W-19 | Mobile/accessibility, focus/Escape, async loader, safe links/CSP cổng | web chat/widget/css; 360/390 px, keyboard, lỗi script hiển thị fallback; không phá trang chủ. AT-31/32 | W-18 |
| W-20 | E2E hai origin/two tenants, cookie bên thứ ba blocked, domain sai, XSS/message spoof; guide đội cổng | tests/e2e + docs/WIDGET_INTEGRATION.md; report Chromium/Firefox và browser mục tiêu; Safari/iOS chưa có môi trường phải ghi chưa chạy. AT-28–32 | W-18/19 |

Gate P3: G3 có bằng chứng mô phỏng. Không gọi đây là đã tích hợp cổng thật khi chỉ chạy localhost.

### P4 / vận hành thiết yếu

| Task | Việc phải làm | Khu vực chính / tiêu chí ra | Phụ thuộc |
|---|---|---|---|
| W-21 | MFA TOTP/recovery, session list/revoke, rotate/reset có audit và quy trình xác minh | auth/main/CLI/schema/UI; replay/recovery reuse/rate-limit/hết phiên/logout Preview bị chặn. AT-02/33 | W-15 |
| W-22 | Rate/concurrency/queue limits và trusted proxy, pause/dependency fail closed | auth/chat/gateway/workers; giả forwarded IP không né limit, fairness tenant nóng, unknown Redis không mở paid call. AT-34 | W-10/17 |
| W-23 | Pricing/runtime nonsecret catalog, usage theo operation chat/query/index, atomic reserve/reconcile/unknown | migrations/usage/AI/CLI/dashboard; concurrent/crash/retry không double charge ledger, unpriced không ghi 0, paid thiếu config bị chặn. AT-35/36 | W-10/22; giá thật E-02 |
| W-24 | Data flow, che PII, raw-log policy, retention jobs/orphan/backup deletion ledger | schemas/chat/logs/jobs/ops; canary secrets không có trong browser/log/export, expiry/purge chéo tenant bị chặn. AT-04/16/17/37 | W-09/13/23 |
| W-25 | Load harness controlled adapter 2s, corpus 100k chunks/10 tenant/30 concurrent, OCR tranh tài nguyên | tests/load/metrics/config; platform p95/queue/memory/pool/429 được báo; tune dựa số đo. AT-38/39 | W-10/22/23 |
| W-26 | Production package/config guards, TLS/proxy/CSP, storage license/security review và dependency/security scan | compose.production example/Docker/gateway/config/runbook; mock/default secrets/bad role fail, không chỉ xóa validator APP_ENV. AT-40/41 | W-17/21/22/24/25 |
| W-27 | Backup/restore cách ly với object manifest/deletion ledger, đo RPO24h/RTO4h | ops/scripts/docs; restore RLS/source/revoke/purge chính xác trước traffic, không tạo paid call. AT-42 | W-09/24/26 |
| W-28 | Metrics/alerts/runbooks và release/migration rollback | health/jobs/logging/docs; người nhận cảnh báo rõ, scenario provider down/full disk/backlog xử lý được. AT-43 | W-23/26/27 |

Gate P4: G4 theo cấu hình đo. Không chạy security/load vào hệ thống bên ngoài; local/staging được cấp phép. Nếu chưa có hạ tầng thật, report local không được nâng thành SLA.

### P5 / nghiệm thu và bàn giao

| Task | Việc phải làm | Đầu ra / tiêu chí ra | Phụ thuộc |
|---|---|---|---|
| W-29 | Chốt môi trường triển khai, policy/retention/data flow, domain/TLS và ngân sách được cấp | Deployment/data-policy nonsecret manifest; không cần IdP/connector | E-01–E-06, W-26/28 |
| W-30 | Bộ nguồn địa phương chính thức, review nghiệp vụ >=200 cases; live semantic/answer/latency smoke | G2 đạt với fingerprint cấu hình định deploy; giữ lỗi và mẫu số report | W-14/23/29 |
| W-31 | Nhúng trên cổng thật, kiểm CSP/mobile/nguồn, UAT Admin và public | AT-44; domain và đơn vị ký nhận rõ, sửa lỗi trước pilot | W-20/29/30 |
| W-32 | Pilot 1–2 tenant, quan sát 7 ngày baseline, restore/runbooks và bàn giao | AT-45; không lỗi chặn, review usage/cost/quality; docs và hạn chế thực tế | W-27/28/31 |

Không hứa ngày hoàn thành khi chưa chạy baseline/tài liệu thực tế hoặc chưa có đầu vào live. Sau W-02 báo ước lượng theo task đã xác minh; cập nhật khi xuất hiện lỗi mới thay vì ghi mốc thời gian suy đoán.

## 6. Chiến lược kiểm chứng

- Unit/contract: parser/schema/format/locator, DTO injection, output/refusal/errors, pricing/reservation; chỉ test hành vi có rủi ro cụ thể.
- Integration: PostgreSQL runtime role + Redis/private storage/ClamAV thật; migration, outbox/worker, concurrency/revocation/purge. Không dùng SQLite thay RLS.
- E2E: Admin A/public A/public B, draft isolation, upload/review/publish/source, cross-origin widget, feedback/mobile/MFA đúng scope.
- Live: opt-in, key/model/data được duyệt, limit tiền/request, lưu usage và report. Mock/contract không thay live.
- System: load/soak, hard crash, security scan, backup restore và deployment Linux thật; ghi riêng các browser/host chưa có.
- Chạy scripts/check.ps1 hoặc .sh phù hợp, generate-api/typecheck/build khi schema/UI đổi, E2E khi luồng đổi. Sau checks bắt buộc đạt chỉ chạy thêm khi có risk/failure mới.
- Mỗi task cập nhật status/checklist/report/resume bằng kết quả thực tế. Không sửa TEST_REPORT.md lịch sử thành ngày mới nếu chưa chạy.

## 7. Artifacts cần có qua các giai đoạn

| Artifact | Phase | Nội dung |
|---|---|---|
| SOURCE_MANIFEST | P1 | URLs/hash/phạm vi/ngày/approval/license notes/fixture label, không PII |
| EXTRACTION_REPORT | P1 | File/page/sheet coverage, warnings, lỗi chưa hỗ trợ và review |
| EVALUATION_DATASET + EVALUATION_REPORT | P2/P5 | Cases/rubric/holdout/fingerprints/quality/latency/cost/reviewer |
| WIDGET_INTEGRATION.md + browser report | P3 | Snippet, CSP/domain, fallback, privacy, kiểm tra đội cổng |
| DATA_FLOW.md / RETENTION_POLICY.md | P4/P5 | Dữ liệu đi đâu, ai đọc, retention/provider/backup và duyệt |
| LOAD_REPORT / SECURITY_REPORT | P4 | Workload/hardware/config, kết quả, vấn đề và fix/acceptance |
| BACKUP_RESTORE_REPORT | P4 | Backup inventory/restore duration/RPO/RTO/deletion/RLS/source |
| RUNBOOKS + PRODUCTION_CHECKLIST | P4 | Triển khai/migration/rollback/alert/incident |
| UAT_REPORT / HANDOVER | P5 | Cổng thật, người nghiệm thu, cấu hình/corpus, giới hạn và vận hành |

Tên có thể điều chỉnh nhỏ theo quy ước repo; chỉ tạo report kết quả sau khi chạy, không tạo report giả với trạng thái pass. Không lưu credentials/trace có token vào docs/Git.

## 8. Đầu vào bên ngoài và công việc không bị chặn

Đọc EXTERNAL_DEPENDENCIES.md. Chỉ phần cần đầu vào bị chặn; tiếp tục các task khác có thể làm local. Người dùng không cần cung cấp IdP/API hồ sơ hay đồng ý triển khai Actions.

| Thiếu | Chưa thể kết luận | Vẫn làm được |
|---|---|---|
| Key/model/data-flow approval | G2 live, paid quality/cost | Code/contract/corpus/Mock/lifecycle/UI |
| Địa phương/reviewer | Corpus nghiệp vụ địa phương được chấp thuận | Public corpus có nhãn/test |
| Domain/cổng thật | AT-44/G5 | Two-origin E2E và guide |
| Hạ tầng/storage production | Hiệu năng/restore môi trường deploy | Config template và report local có giới hạn |
| UAT owner/policy | accepted_uat/production ready | Chuẩn bị hồ sơ và kiểm tra kỹ thuật |

## 9. Điều kiện dừng và xử lý rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Rò tenant/secret, public dùng draft/revoked | Chặn release; ưu tiên fix và regression, không chấp nhận bằng điểm trung bình |
| OCR/table không giữ đủ nghĩa | Needs_review hoặc fail rõ; corpus review trước publish; không tạo dữ liệu thiếu rồi gọi success |
| AI trả lời thiếu căn cứ | Giảm phạm vi/evidence/prompt/ranking dựa case, chạy lại holdout; chưa đạt thì chưa public |
| Chi phí đột biến hoặc giá không biết | Fail closed paid operations, giữ unknown usage/reservation để đối soát |
| Host không chịu baseline | Đo bottleneck/worker/pool/storage, điều chỉnh cấu hình hoặc công bố quy mô thấp hơn bằng quyết định mới; không che kết quả |
| Storage hiện tại không phù hợp production | Review lựa chọn S3-compatible được duy trì; migration object có manifest, giữ contract, không tự tạo tài nguyên |
| Backup hồi sinh dữ liệu đã xóa | Restore cách ly, apply deletion ledger trước public; fail drill chặn G4 |
| Đặc tả cũ/công cụ sinh checklist kéo lại scope | Archive v1, chỉ dùng v2 hiện hành; W-01 sửa generator trước khi chạy |

## 10. Kết thúc lượt P0

Lượt này bàn giao tài liệu cụ thể để người dùng xem. Không code app, không migration, không chạy test tạo dữ liệu, không gọi AI tính phí, không đổi .env và không mở production.

Bước code kế tiếp bắt đầu W-01/W-02, rồi P1 theo bằng chứng baseline. Mục tiêu không chỉ là đổi nhãn M2; đích cuối là G0–G5 của sản phẩm hỏi đáp công khai đã được xác định.

W-27/AT-42 phải kiểm trường hợp xóa xảy ra sau thời điểm backup: giữ deletion ledger mới nhất tách khỏi snapshot phục hồi, replay trước mở public và xác minh nguồn/derived answer không hồi sinh. Không chỉ restore ledger cũ từ backup rồi kết luận deletion policy đạt.
