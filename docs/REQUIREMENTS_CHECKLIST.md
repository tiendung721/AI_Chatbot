# Truy vết yêu cầu và nghiệm thu v2.0

Ngày lập: 13/11/2026. Nguồn yêu cầu: [master spec v2](../CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md).
Kế hoạch công việc: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Hiện trạng: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

## 1. Quy tắc theo dõi

- FR/NFR là yêu cầu hiện hành; W là task kế hoạch; AT là kịch bản nghiệm thu v2. Các mã T-01–T-70 cũ giữ ở bản lưu, không đánh số lại thành AT để giả rằng đã test v2.
- Trạng thái in_progress trong bảng này có nghĩa đã có một phần code hoặc bằng chứng lịch sử liên quan, chưa nghiệm thu đủ case v2. not_started nghĩa chưa có bằng chứng triển khai cho tiêu chí mới.
- P0 ngày 13/11/2026 chỉ tài liệu; sau yêu cầu bắt đầu code, P1/W-01–W-09 đã triển khai và kiểm thử local. Live/load/security/restore toàn hệ thống chưa nghiệm thu.
- Kết quả 56 backend/6 Chromium ngày 10/11/2026 là lịch sử Mock/local, không phải 45 AT mới đã pass.
- Khi hoàn thành cập nhật từng AT với command, ngày, source manifest/hash, môi trường, expected/actual, artifact nonsecret và giới hạn.
- W-01 đã đổi scripts/update_requirement_checklist.py thành validator chỉ đọc FR/NFR/W/AT. Tool không tạo lại bảng hoặc tự đổi trạng thái test.

## 2. Yêu cầu → công việc → kiểm tra

| Yêu cầu | Task | AT liên quan | Gate |
|---|---|---|---|
| FR-01 Đa tenant | W-04/07/10/17/23/24 | AT-01/11/15/18/19/25/35/37 | G1/G4 |
| FR-02 Admin | W-15/21 | AT-02/33 | G4 |
| FR-03 Cấu hình nội dung | W-15/16 | AT-03/04/13 | G1 |
| FR-04 Nhập/upload | W-04/05/08 | AT-05/10/12 | G1 |
| FR-05 Scanner/parser/OCR | W-06/07 | AT-06/07/08/11 | G1 |
| FR-06 Review/metadata | W-04/06/08 | AT-08/09/13 | G1 |
| FR-07 Kho/version | W-04/08 | AT-09/12/14 | G1 |
| FR-08 Xuất bản | W-16 | AT-13/14/15/26 | G1/G2 |
| FR-09 Hỏi đáp | W-10/11/12/14 | AT-18/20/21/22/23 | G1/G2 |
| FR-10 Nguồn | W-09/13 | AT-15/16/19/24 | G1/G2 |
| FR-11 Nhúng | W-17/18/19/20/31 | AT-28/29/30/31/32/44 | G3/G5 |
| FR-12 Phiên chat bền vững | W-07/13 | AT-11/24/25 | G1 |
| FR-13 Phản hồi/tổng quan | W-15/24 | AT-27/37 | G1/G4 |
| FR-14 Evaluation | W-03/14/16/30 | AT-22/23/26/44 | G2/G5 |
| FR-15 Giới hạn | W-22/23 | AT-34/35/36 | G4 |
| FR-16 Lifecycle | W-09/24/27 | AT-15/16/17/37/42 | G1/G4 |
| FR-17 Runtime Developer | W-10/15/16/23/26 | AT-04/18/26/36/40 | G1/G4 |
| FR-18 Vận hành | W-25/26/27/28/32 | AT-38/39/40/41/42/43/45 | G4/G5 |
| NFR-01 Isolation | W-04/07/10/17/23/24 | AT-01/11/15/19/25/35/37 | G1/G4 |
| NFR-02 Security | W-06/17/20/21/24/26 | AT-02/04/06/29/30/32/33/40/41 | G1/G4 |
| NFR-03 Quality | W-03/06/11/12/13/14 | AT-07/08/18/19/20/21/22/23 | G2 |
| NFR-04 Durability | W-05/07/09/13/16 | AT-10/11/13/14/15/16/24/25 | G1/G4 |
| NFR-05 Performance | W-10/22/25 | AT-18/34/38/39 | G4 |
| NFR-06 Cost | W-22/23 | AT-34/35/36 | G4 |
| NFR-07 Privacy | W-09/24/27 | AT-16/17/27/37/42 | G4 |
| NFR-08 UX/embed | W-18/19/20/31 | AT-28/29/30/31/32/44 | G3/G5 |
| NFR-09 Operations | W-26/27/28/32 | AT-40/41/42/43/45 | G4/G5 |
| NFR-10 Evidence | W-01/02/14/25/30/32 | AT-22/23/38/39/44/45 | G0–G5 |

## 3. Kịch bản nghiệm thu

Mỗi dòng có thể cần nhiều test; một test không mặc nhiên chứng minh toàn bộ dòng. Bằng chứng lịch sử chỉ chỉ ra nơi bắt đầu đối chiếu.

| AT | Tình huống và kết quả phải chứng minh | Phase | Hiện trạng / bằng chứng lịch sử |
|---|---|---|---|
| AT-01 | Hai tenant A/B, runtime không owner/superuser/BYPASSRLS; thiếu context default-deny, pool reuse và FK chặn đọc/ghi/gắn version chéo; lặp cho mọi bảng mới | P1/P4 | tested_local (schema P1) — PostgreSQL thật, baseline RLS và test_p1 mở rộng batch/receipt/metadata FK chéo tenant; lặp lại cho schema P2–P4 khi bổ sung |
| AT-02 | Login/đổi password/idle/absolute expiry/logout/rotate Admin; session cũ và Preview mất quyền, một Admin active | P2/P4 | in_progress — auth và test_preview_token_stops_working_after_admin_logout đã có; chưa đủ session UI |
| AT-03 | Lưu tên/Instructions/starters/màu/đầu mối chỉ thành draft; không đổi public khi chưa publish; không có tenant switcher | P2 | in_progress — M1 có E2E cấu hình; đầu mối/validation mới chưa chứng minh |
| AT-04 | Inject model/provider/key/runtime/tenant và nested field bị reject; không lộ trong UI/API/errors/export/log, Instructions không đổi quyền | P2/P4 | in_progress — test_policy model injection + test_no_technical_metadata M1, mở rộng mọi endpoint mới |
| AT-05 | Upload tối đa 10 file/batch với kết quả từng file, kiểm actual bytes/body/extension/MIME; partial failure không success giả | P1 | tested_local — unit giới hạn/formats, E2E CSV/Excel và test_p1 batch gồm file hợp lệ/exe/empty có kết quả riêng; không suy thành security fuzz toàn diện |
| AT-06 | Giả MIME/empty/oversize/encrypted/zip bomb/XML/script/macro; EICAR quarantine; scanner down/stale signature fail closed, parser không network/key | P1/P4 | in_progress — fixture MIME/XML/EICAR/scanner down và subprocess limits có lịch sử; security corpus/signature mới cần kiểm |
| AT-07 | PDF text/scan vie+eng, DOCX/PPTX/text/CSV/HTML/ảnh có coverage/locator thực; layout khó fail/review rõ, không bỏ trang âm thầm | P1 | tested_local trên corpus đã khai báo — regression formats/OCR + 21/22 originals trích xuất, 1 HTML rỗng fail dự kiến, 1 scan dẫn xuất; 508 trang PDF. Layout/ngữ nghĩa ngoài corpus chưa chứng minh; xem EXTRACTION_REPORT |
| AT-08 | XLSX merged/header/unit/formula cached/hidden sheet; review chọn section/revision/ack warnings; edit làm mất approval, stale/foreign sections bị chặn | P1 | tested_local cho cơ chế review/revision — regression XLSX/E2E, review ready và race 200/409; thêm 3 XLSX thật. Header/unit/layout phức tạp vẫn cần duyệt người, chưa có chứng nhận ngữ nghĩa tổng quát |
| AT-09 | Metadata unknown=null, hiệu lực đúng, source URL/hash/jurisdiction/supersedes có kiểm tra; nguồn địa phương B không dùng cho A | P1/P2 | tested_local phần P1 — strict/null/dates/URL/tags/classification/supersedes và FK/RLS; original SHA256 giữ nguyên. Không tự xác minh hiệu lực pháp lý; chất lượng retrieval thuộc P2 |
| AT-10 | Retry POST upload cùng ID/payload không nhân document/version/object/job; khác payload conflict; retry worker không nhân chunks | P1 | tested_local — test_batch_retry_concurrency_and_payload_conflict + regression worker; cùng request ID replay receipt, khác fingerprint 409, partial batch giữ kết quả |
| AT-11 | Kill worker thật giữa parse và purge, lease hết hạn/reclaim/fencing; revoke/review/publish/purge đồng thời không hồi sinh dữ liệu | P1/P4 | tested_local phần P1 — kill process sau parser và sau S3 delete trước DB commit; recovery với lease chủ động hết hạn, stale parser/revoke/purge và review race. Broker/host outage/load còn P4 |
| AT-12 | Tạo >200 versions, lọc/search/page/sort ổn định; detail/original/versions/review đúng quyền; published version immutable/diff đúng | P1 | tested_local — API 205 versions/11 pages, lịch sử phân trang không body lớn, filter/diff/immutable và E2E picker giữ lựa chọn qua trang; source trỏ test_p1 và p1.spec.ts |
| AT-13 | Public chưa thấy draft/unapproved/not ready; validation gắn hash/runtime và hết hạn, hai tab publish conflict; publish transaction atomic | P2 | in_progress — M1 draft/revision/stale-validation test; evaluation/expiry/runtime đầy đủ cần bổ sung |
| AT-14 | Version cũ vẫn đúng nội dung, rollback kiểm current policy/profile/effectivity; không hồi phục nguồn/quyền đã thu hồi hoặc hạ runtime | P2 | in_progress — M1 immutable/rollback/revocation tests, bổ sung v2 gates |
| AT-15 | Revoke/pause giữa retrieval/generate/commit, xem source/result/SSE cũ sau revoke và rollback; không phát nguồn/đáp án bị cấm | P1/P2 | in_progress — test_revocation_during_generation/old_result_source_sse có lịch sử, cần mở rộng cache/history/domain |
| AT-16 | Purge live object/chunks/vectors/sections/review/derived answers đúng tenant, retry được, giữ IDs/tombstone tối thiểu; không claim backup đã xóa | P1/P4 | tested_local phần P1 — regression purge + receipt filename redaction + stale worker/hard-kill recovery. Backup/provider copies và retention định kỳ còn P4 |
| AT-17 | Object orphan qua upload/DB crash được phát hiện; dry-run/grace không xóa active upload, sweeper idempotent và có metric | P1/P4 | tested_local nền tảng P1 — CLI dry-run/apply, grace >=24h, tenant/DB/ETag/size, lock với upload, audit counts và idempotency. Batch tối đa 10.000 objects, scheduler/checkpoint toàn kho còn P4 |
| AT-18 | Query embedding không giữ DB connection; profile/dimension/fingerprint sai bị chặn; retrieval lọc ACL/release/effectivity trước ranking | P2 | in_progress — vector/profile/RRF test lịch sử, query embedding hiện nằm trong transaction |
| AT-19 | Model bịa evidence/locator/URL bị chặn; nguồn resolve đúng phiên bản/phần được duyệt; original public chỉ khi cho phép; source chéo session không đọc | P2 | in_progress — validator/source ownership có lịch sử; download permission và tất cả endpoints cần kiểm |
| AT-20 | Tiếng Việt có/không dấu, lỗi gõ nhẹ, follow-up trong cùng session; không dùng history tenant/session khác hay đáp án cũ làm bằng chứng | P2 | in_progress — lexical/unit tiếng Việt có; bounded conversation và semantic corpus chưa đủ |
| AT-21 | Thiếu nguồn/mơ hồ/mâu thuẫn/hết hiệu lực/out-of-scope/câu hỏi hồ sơ cá nhân được xử lý đúng; không CTA login hoặc claim đã thực hiện nghiệp vụ | P2 | in_progress — no-source Mock có; live và tập tình huống v2 chưa nghiệm thu |
| AT-22 | Dataset >=50 ban đầu/>=200 trước live nghiệm thu, holdout >=20%, nguồn/hash/reviewer; retrieval recall@8 >=90% trên subset có đáp án | P2/P5 | not_started — chưa có dataset/report live theo v2 |
| AT-23 | Live AI đạt đúng nghiệp vụ/groundedness/clarify-refuse >=95% ở subset tương ứng; citation valid100%, 0 lỗi trọng yếu, chấm người và báo mẫu số | P2/P5 | not_started — blocked_external_dependency cho live key/data/reviewer |
| AT-24 | SDK timeout/429/refusal/incomplete/error trả trạng thái đúng, không raw provider data/Mock fallback; cancel không tạo result/cost giả | P2 | in_progress — adapter contract có, chưa live failure coverage đầy đủ |
| AT-25 | POST timeout/retry cùng client_request_id, one-live-turn/session, SSE reconnect/replay/terminal result/expiry/ownership, không nhân AI call | P2 | in_progress — M1 idempotency/SSE có lịch sử; mở rộng cost/deadline và browser |
| AT-26 | Evaluation/preflight gắn đúng draft/corpus/runtime hash; đổi nguồn/runtime hết hiệu lực validation và thay model cần đánh giá lại | P2 | in_progress — runtime fingerprint/hash cơ bản có; evaluation gate chưa đủ |
| AT-27 | Feedback hữu ích/không hữu ích đúng turn/session, dashboard counts thật theo tenant; Admin xem dữ liệu đã che PII, không raw transcript tùy ý | P2/P4 | in_progress — feedback/counts M1 có; privacy/UI thêm chưa chứng minh |
| AT-28 | Hai origin portal khác origin chatbot, hai public_key; embed đúng đơn vị, không phụ thuộc third-party cookies, direct chat fallback | P3 | not_started — loader đang từ chối origin khác |
| AT-29 | frame-ancestors per tenant trong HTTP HTML response, domain không cấp phép bị chặn; Admin không bị frame; nới widget không nới Admin CORS | P3/P4 | not_started — chưa có domain/CSP nhúng khác origin đầy đủ |
| AT-30 | Giả postMessage origin/source/schema bị bỏ; targetOrigin exact; parent/URL/log không nhận token/nội dung; reload tạo session mới an toàn | P3 | not_started — kiểm cơ chế mới khi triển khai |
| AT-31 | Mobile 360/390px không tràn, nguồn/mở đóng/focus/Escape/keyboard và thông báo AI/privacy đọc được | P3 | in_progress — M1 mobile390 E2E có; accessibility/widget khác origin chưa đủ |
| AT-32 | XSS/link/HTML/CSP/malicious parent/loader fail không thực thi script hay phá cổng; browser mục tiêu có report riêng | P3/P4 | in_progress — React text/basic sanitizer có; cross-origin/browser/security cần kiểm |
| AT-33 | MFA enroll/challenge/recovery reuse/reset/session revoke; secret mã hóa, recovery hash, production không bỏ MFA | P4 | not_started — chưa có MFA production |
| AT-34 | Limits session/IP/tenant/global, giả forwarded IP, tenant nóng, overload và Redis down; chặn paid calls mới đúng policy, có Retry-After | P4 | in_progress — Redis rate count cơ bản có; trust proxy/concurrency/budget path chưa đủ |
| AT-35 | Concurrent reserve quota chat/query embedding/indexing, idempotent operation, retry/timeout/crash/unknown reconcile không double-count hoặc hoàn tiền mù | P4 | not_started — chưa atomic budget ledger |
| AT-36 | Giá thiếu=unpriced, không 0; paid production thiếu pricing/budget fail closed; usage thực và limit hiển thị không lộ model | P4 | in_progress — usage unpriced có; pricing/budget controls chưa có |
| AT-37 | Retention hết hạn đúng chat/feedback/session/audit/temp, canary PII/secret trong log/browser/report, data-flow và quyền đọc phù hợp | P4 | not_started — chưa retention jobs/privacy acceptance v2 |
| AT-38 | 10 tenant/100k chunks/30 concurrent/tenant nóng; controlled adapter2s, p95 endpoint<=1s/retrieval<=500ms/queue<=5s/final<=15s, errors<1% | P4 | not_started — mục tiêu thiết kế, chưa đo; báo 429/provider riêng |
| AT-39 | 30 phút load+2 giờ soak, OCR tranh tài nguyên và burst/provider latency; không mất job/leak pool/memory, báo hardware/tuning/live p95 riêng | P4 | not_started — chưa load/soak |
| AT-40 | Production reject mock/default secrets/bad role/missing TLS-MFA-budget-policy; images/nonroot/migration/health/script Linux không reset dữ liệu | P4 | in_progress — fail-closed/local guards đã có; hiện production bị khóa toàn bộ |
| AT-41 | Dependency/container/upload/parser/XSS/CSRF/session/prompt injection scan; không critical/high unresolved thuộc release scope | P4 | not_started — chưa security scan nghiệm thu |
| AT-42 | Backup DB+objects+config+deletion ledger restore cách ly, RPO<=24h/RTO<=4h; RLS/source/revoke/purge đúng trước traffic | P4 | not_started — chưa restore drill |
| AT-43 | Alert có người nhận, health/queue/cost/storage/AI metrics; drill outage/backlog/storage full và rollback/recover theo runbook | P4 | in_progress — health/worker ping có; alert/runbook drill chưa đủ |
| AT-44 | Corpus địa phương/reviewer/policy/domain thật, widget chạy trên cổng thật, AI live/report/chi phí và UAT Admin/public được ký nhận | P5 | not_started — blocked_external_dependency theo đầu vào E-01–E-06 |
| AT-45 | Pilot 1–2 tenant/7 ngày baseline, review chất lượng/usage/incident; bàn giao docs/admin/ops/backup, không lỗi chặn còn mở | P5 | not_started — chưa pilot/UAT |

## 4. Liên hệ với 70 test IDs v1

Bảng này chỉ chuyển phạm vi, không chuyển trạng thái pass. Bảng v1 nguyên văn tại [archive](archive/2026-11-10-v1/REQUIREMENTS_CHECKLIST.md).

| T-ID lịch sử | Xử lý v2 |
|---|---|
| T-01, T-02, T-03, T-04, T-05, T-06, T-07, T-08, T-09, T-61 | Giữ phần tenant/session/source/cache/worker: AT-01/11/15/19/25; artifact ngoài phạm vi không bắt buộc |
| T-10, T-11, T-12, T-13, T-14, T-15, T-69, T-70 | Giữ technical isolation/DTO/profile/schema: AT-04/18/26/40; không cần capability UI |
| T-17, T-18, T-19, T-20, T-21, T-22, T-23, T-32 | Giữ scanner/parser/OCR/worker: AT-05/06/07/08/10/11 |
| T-24, T-25, T-26, T-27, T-28, T-29 | Giữ draft/publish/revocation/hiệu lực: AT-09/13/14/15/26 |
| T-30, T-31, T-33, T-38, T-49, T-51, T-52, T-53, T-60 | Giữ Q&A/source/errors/stream/UI: AT-19/20/21/23/24/25/31/32 |
| T-55, T-56, T-57, T-58, T-59 | Giữ quota/guards/purge document-chat/restore: AT-16/17/35/36/37/40/42; phần attachment công dân T-58 ngoài phạm vi |
| T-67, T-68 | Giữ bootstrap không phá dữ liệu/Engine failure: AT-40 và regression nền tảng |
| T-16, T-34, T-35, T-36, T-37 | out_of_scope: compatibility nâng cao và crawler; SSRF khi tool download nguồn được dùng vẫn phải kiểm soát riêng |
| T-39, T-40, T-41, T-42, T-43, T-44, T-45, T-46, T-47, T-48, T-50, T-54, T-62 | out_of_scope: personal tools/OIDC/Action/connector/tool loop |
| T-63, T-64, T-65, T-66 | out_of_scope: attachment công dân, web search, code, voice/image |

## 5. Quy tắc hoàn thành

- AT an toàn/tenant/citation/revoke/MFA/budget/restore có lỗi chặn thì gate liên quan chưa đạt.
- not_started/out_of_scope/blocked_external_dependency không được cộng vào số case pass.
- Report benchmark giả lập, live API và UAT có scope riêng; không ghi một chữ pass chung cho mọi môi trường.
- Gate G2/G4/G5 phải được nghiệm thu với config/corpus/môi trường tương ứng; thay đổi đáng kể cần chạy lại phần liên quan.

## 6. Bằng chứng P1 ngày 13/11/2026

Môi trường Windows/Docker Desktop Linux Engine, PostgreSQL/RLS/private storage/ClamAV/parser thật, AI Mock và embeddings disabled. [TEST_REPORT](TEST_REPORT.md) ghi commands và kết quả: 64 backend pass + 1 opt-in skipped, corpus riêng 1 pass, 8 Chromium pass; lint/type/build đạt. [P1 report](P1_IMPLEMENTATION_REPORT.md) ánh xạ W-01–W-09; [extraction report](EXTRACTION_REPORT.md) và [manifest nguồn/hash](../fixtures/public_sources/manifest.json) công bố cả HTML thất bại có dự kiến.

Expected/actual cho AT-10 là cùng batch/payload chỉ một version/job/object và payload khác 409; test đạt. AT-12 dùng 205 versions qua 11 trang, history phân trang và UI giữ chọn qua trang; test đạt. AT-11/16/17 dùng fixture process/tenant mới, revoke/purge không hồi sinh và sweeper không xóa object đang được DB trỏ; test đạt trong giới hạn local đã nêu. Source: [integration P1](../apps/api/tests/integration/test_p1.py), [corpus test](../apps/api/tests/integration/test_public_corpus.py), [browser P1](../tests/e2e/p1.spec.ts). Artifact nonsecret catalog/diff ở .local/evidence; traces/credentials không công bố.

Các trạng thái tested_local chỉ áp dụng phần/corpus nêu rõ trong từng dòng, không đổi AT-22/23 hoặc gate G2/G4/G5 thành passed. Phần chưa chạy, layout/ngữ nghĩa cần duyệt người, retention định kỳ, production fault/security/load/restore và live/UAT vẫn được theo dõi ở phase tiếp theo.
