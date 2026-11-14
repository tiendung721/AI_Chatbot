# Thay đổi phạm vi v2.0 và phương án bàn giao

Ngày: 13/11/2026.
Căn cứ: người dùng xác định chatbot chỉ nhúng vào cổng thông tin phường/xã để người dân nhập câu hỏi và nhận câu trả lời có nguồn; yêu cầu chuẩn bị đặc tả/kế hoạch đầy đủ trước code.

## 1. Quyết định sản phẩm

Đích bàn giao là nền tảng hỏi đáp công khai, đa đơn vị, có Admin quản lý tri thức, nguồn dẫn và vận hành an toàn. Admin vẫn xác thực. Người dân không cần tài khoản và không thực hiện giao dịch/hồ sơ cá nhân qua chatbot.

Đặc tả v2.0 tại root thay thế v1.0. Giữ v1 nguyên văn và các tài liệu bị thay trong archive để không mất lịch sử hoặc nhầm rằng các tính năng bị bỏ đã được triển khai.

## 2. Đối chiếu yêu cầu cũ

| Mã v1 | Quyết định v2 |
|---|---|
| REQ-01 Đa tenant | Giữ FR-01 |
| REQ-02 Public và personal authenticated | Chỉ giữ public Q&A/session ẩn danh; citizen auth và ownership hồ sơ ngoài scope |
| REQ-03 File/text/website | Giữ file/text/OCR; bỏ website sync trong bản này |
| REQ-04 Đủ Capabilities | Giữ knowledge retrieval; web/attachments/code/image/voice/extensions ngoài scope |
| REQ-05 Một Admin | Giữ, có MFA production/recovery/rotate |
| REQ-06 Actions | Ngoài scope; không có API nghiệp vụ hoặc thao tác ghi của công dân |
| REQ-07 Docker/cloud-neutral | Giữ baseline single-host Linux Docker/S3-compatible; không bắt buộc HA |
| REQ-08 Usage/budget/monitor/backup | Giữ mức cần vận hành, không làm BI/billing sâu |
| REQ-09 Vận hành thực tế | Giữ trong phạm vi Q&A, gate đo được thay cho đủ M0–M8 cũ |
| REQ-10 Developer-only AI | Giữ nguyên ranh giới, Admin không xem/chọn model/key |

CAP-01 cũ tương ứng FR-09/10. CAP-02–CAP-09 cũ out_of_scope. Không cần UI checkbox cho các khả năng này; giữ API cũ an toàn để tương thích nếu cần, không viết lại code chỉ để xóa field.

## 3. Đối chiếu milestone

| Milestone v1 | Xử lý trong v2 |
|---|---|
| M0/M1 | Giữ nền tảng và bằng chứng local lịch sử; regression trong P1/P2 |
| M2 | Hoàn thiện tri thức trong P1 và retrieval/quality trong P2 |
| M3 | Giữ Admin/preflight/evaluation; website sync/crawler ngoài scope |
| M4 | out_of_scope toàn bộ citizen identity/Actions |
| M5 | out_of_scope các capabilities mở rộng |
| M6 | Chỉ giữ usage/rate/concurrency/budget/retention tối thiểu trong P4 |
| M7 | Giữ security/load/restore/deployment, không bắt buộc HA lớn |
| M8 | P5 cho corpus/domain/live Q&A/UAT/pilot, bỏ IdP/connector gates |

Không gọi P1 hay M2 cũ là hoàn thành sản phẩm: còn G2 AI thật, G3 nhúng khác origin và G4/G5 vận hành/nghiệm thu. Ngược lại, không đòi các tính năng OUT làm điều kiện hoàn thành v2.

## 4. Mặc định phương án, chưa phải kết quả đã đạt

- Không crawler; tự tuyển corpus công khai cho local, Admin nạp thủ công.
- Iframe origin chatbot + exact-origin allowlist/CSP; bearer session trong iframe, không cookie bên thứ ba/SSO cổng.
- CLI/report evaluation đủ dùng, không bắt buộc evaluation dashboard lớn.
- Một host ban đầu; backup restore RPO24h/RTO4h thay mục tiêu đề xuất RPO1h của v1, vì chưa có yêu cầu PITR/HA và dữ liệu public là trọng tâm.
- Baseline benchmark 10 tenant/100k chunks/30 active turns, các ngưỡng ở spec cần đo; chưa là SLA.
- Mặc định retention cần đơn vị duyệt trước public. Chưa chọn model/provider pricing, host, domain hoặc thời điểm go-live thay người dùng.
- P0 chỉ tài liệu. Không đổi production validator, cấu hình/secrets, code hoặc migrations trong lượt này.

## 5. Những file được điều chỉnh và cách đọc

Master spec/plan/checklist/status/resume/dependencies là nguồn hiện hành. DECISIONS.md bổ sung quyết định v2; README/AGENTS/architecture/security/deployment/operations dẫn về scope mới. M2_PLAN.md trở thành trang chuyển tiếp tới P1/P2.

TEST_REPORT.md được giữ nguyên vì chưa chạy test mới. Các tài liệu API/DB/Admin mô tả code hiện tại vẫn có giá trị; chúng không chứng minh target v2 đã có đủ code. Công cụ generator checklist v1 cần sửa W-01 ở lượt code.

## 6. Trước khi code tiếp

Bộ tài liệu đủ để người dùng rà soát scope, các mặc định nghiệm thu và trình tự. Chưa suy yêu cầu chuẩn bị tài liệu thành lệnh triển khai ngay. Khi người dùng yêu cầu bắt đầu code, thực hiện W-01/W-02 rồi P1; đầu vào live/domain chỉ hỏi khi đến bước cần.
