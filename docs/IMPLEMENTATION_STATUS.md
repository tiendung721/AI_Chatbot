# Trạng thái triển khai v2.0 — sau P1 local

Cập nhật: **13/11/2026**, Asia/Saigon. Người dùng đã yêu cầu bắt đầu code theo W-01–W-09.
**P1 đã triển khai và kiểm thử local trong phạm vi đã chốt. Toàn bộ sản phẩm chưa hoàn thành; AI thật và production chưa được mở.**

## 1. Trạng thái theo giai đoạn

| Phase | Trạng thái | Bằng chứng và giới hạn |
|---|---|---|
| P0 — tài liệu | implemented_local | Spec v2/plan/checklist đã được rà soát; người dùng cho triển khai P1. Không suy thành phê duyệt SLA/hạ tầng/retention cho production |
| P1 — tri thức | tested_local | W-01–W-09 có code/test: metadata/source/classification, batch receipts, kho/lịch sử phân trang, review/diff/text version, corpus và recovery/purge/orphan cleanup. Xem P1_IMPLEMENTATION_REPORT.md |
| P2 — hỏi đáp/AI/Admin | in_progress | Kế thừa chat/source/Preview/release; chưa live semantic/answer evaluation, bounded history, preflight/evaluation đầy đủ. Query embedding còn trong transaction |
| P3 — widget khác origin | not_started | Widget vẫn cùng origin; chưa domain/CSP/cross-origin nghiệm thu |
| P4 — vận hành | in_progress | Có local Docker/health/rate cơ bản; chưa MFA, atomic budget/pricing, retention định kỳ, load/soak/security scan/restore/production guards |
| P5 — live/UAT/pilot | blocked_external_dependency | Cần key/model/budget/policy, đơn vị/reviewer/corpus duyệt, domain/hạ tầng/UAT. Không yêu cầu IdP/API hồ sơ |

P1 tested_local không có nghĩa toàn bộ 45 AT hay G1–G5 đã đạt. OUT-01–OUT-08 vẫn ngoài phạm vi. M0–M8/T-ID cũ là lịch sử.

## 2. Đã bổ sung trong P1

- Migration tiến 0004: metadata/version updated_at, supersedes cùng tenant, approval actor/time; upload_batches/upload_receipts có FORCE RLS và composite FK.
- Metadata có source URL/ngày thu thập/phạm vi/phân loại/tag/quan hệ phiên bản; dữ liệu chưa rõ là null, URL chỉ ghi nhận chứ không tự tải. Sửa metadata/review làm mất approval; published version không sửa.
- Batch request fingerprint và receipt từng file; retry/concurrent cùng ID không nhân object/version/job. File lỗi có kết quả riêng. Không xóa object mù khi COMMIT có kết quả chưa rõ.
- Kho và history có phân trang; history không trả mọi body lớn. UI tìm/lọc và chọn phiên bản qua nhiều trang; so sánh nội dung/metadata; tạo phiên bản văn bản mới.
- Review được cả extraction ready chưa publish, không chỉ needs_review. Nguồn nội bộ/hạn chế không approve public; Preview với provider ngoài chặn tài liệu chưa được phép trước khi gọi AI.
- DOCX đường dẫn ZIP Windows được chuẩn hóa trong bản sao parser; giữ original, kiểm collision/traversal/XML/bomb; cảnh báo chữ ký chưa xác minh. Control chars PDF được làm sạch có warning.
- Purge che filename trong upload receipt, xóa derived content và chống worker cũ hồi sinh. Orphan CLI mặc định dry-run, đúng prefix tenant, grace >=24h, có lock với upload và đối chiếu ETag/size/DB.
- Corpus 22 file gốc/hash duy nhất, 7 nhóm chủ đề/hai tenant fixture; 21 file trích xuất, một HTML JavaScript rỗng báo lỗi có dự kiến; thêm một ảnh OCR dẫn xuất có nhãn.

## 3. Kiểm thử thực sự đã chạy

| Kiểm tra | Kết quả |
|---|---|
| Baseline đầu lượt check.ps1 | 56 backend pass, Ruff/mypy và frontend build pass |
| Baseline Chromium | 6 pass |
| check.ps1 cho bản P1 | Ruff/mypy pass, 64 backend pass + 1 opt-in corpus skipped, frontend production build pass |
| Backend source cuối sau guard dữ liệu và bổ sung assertions | 64 pass + 1 corpus skipped; Ruff pass, mypy 29 source files pass |
| Corpus opt-in/private storage/ClamAV/parser/OCR | 1 test pass; 22 file gốc + 1 derived scan, không gọi AI và không publish |
| OpenAPI → TypeScript và pnpm typecheck | Pass |
| Chromium cuối: 6 regression + 2 luồng P1 | 8 pass (49,4 giây), sau bản build UI cuối |
| Docker local readiness và worker/ingester ping | Pass |

Kết quả browser cuối và số thời gian chính xác được ghi trong TEST_REPORT.md/P1_IMPLEMENTATION_REPORT.md. Những lượt browser lỗi trong quá trình sửa được ghi là lịch sử lỗi, không cộng thành pass.

## 4. Giới hạn còn lại

- Không có live AI/semantic benchmark hoặc nghiệm thu nghiệp vụ; corpus chỉ kiểm kỹ thuật trích xuất. Không chứng nhận chữ ký số/hiệu lực pháp lý.
- Metadata có allow_public_download để giữ chính sách, nhưng bản public hiện dùng source excerpt viewer; UI không quảng bá tải original công khai. Phần source policy/viewer mở rộng tiếp ở P2.
- Orphan cleanup hiện theo CLI/batch giới hạn tối đa 10.000 objects, có dry-run/audit; chưa scheduler/checkpoint vận hành toàn kho/retention tự động hoặc xử lý backup/provider copies.
- Hard-kill được kiểm tra bằng process fixture sau parser/S3 và chủ động hết lease để tái lập nhanh; chưa fault-injection broker/host hoặc load/restore toàn hệ thống.
- Header/unit/layout phức tạp vẫn cần Admin kiểm tra; số trang đọc đủ không có nghĩa đúng ngữ nghĩa. Không tự chạy JavaScript trang nguồn.
- Production vẫn bị khóa. Không nâng P1 thành sản phẩm hoàn chỉnh hoặc đã tích hợp cổng thật.

## 5. Điểm tiếp theo

Đọc RESUME.md và P1_IMPLEMENTATION_REPORT.md. Công việc P2 bắt đầu W-10 khi được yêu cầu: tách query embedding khỏi transaction, retrieval/answer/history/evaluation và preflight. Giữ scope Q&A công khai; không tự triển khai Actions/citizen auth.
