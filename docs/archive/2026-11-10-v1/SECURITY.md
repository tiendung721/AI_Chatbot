# Bảo mật và giới hạn hiện tại

Các ranh giới đã có code/test: tenant context phía server, runtime RLS/default-deny, composite FK, Admin DTO forbid extra, CSRF/Origin, password Argon2id, giới hạn đăng nhập bằng Redis atomic counter, cookie HttpOnly/SameSite, idle/absolute expiry và thu hồi phiên; Preview gắn phiên Admin. Password cấp lần đầu phải đổi; rotate-admin vô hiệu người cũ và phiên cũ.

Nguồn chỉ từ phiên bản được chọn, đúng tenant, ready/hiệu lực/approval khi public và chưa thu hồi. Backend tự cấp evidence IDs và locator, không nhận URL/số trang do model bịa. Sau generate khóa/kiểm tra nguồn hiện tại trước commit. Kết quả cũ và SSE replay không phát lại nội dung có citation đã thu hồi. React render text, không thực thi Markdown HTML/script. Không expose tool executor; các capability chưa triển khai luôn không được cấp.

API/worker không có migration URL. Secrets chỉ ở `.env` local hoặc môi trường máy chủ; Docker context/Git bỏ qua `.env`, `.local`, trace và credentials. OpenAI adapter không đưa raw response/log/secret ra client, không đặt temperature/reasoning không được cấu hình. Không thu hidden chain-of-thought.

Production **bị chặn vô điều kiện ở Settings** trong giai đoạn này. Những phần chưa đạt: MFA/recovery, OIDC thật, scanner/parser/OCR, SSRF crawler, Action confirmation/reconciliation, budget reservation/pricing, retention/purge, đầy đủ CSP nonce/domain allowlist, audit vận hành mở rộng, security scan/load/restore/UAT. CSP hiện dùng inline cho Next.js; chỉ hỗ trợ nhúng cùng nguồn. Chưa kết luận tuân thủ pháp luật hoặc được xử lý hồ sơ thật.

MinIO source upstream đã archive; local source build giữ checksum/license. Trước production phải review thành phần lưu trữ được duy trì, license và CVE. Đọc `EXTERNAL_DEPENDENCIES.md` và go-live gates mục 19.4 trong master spec; không bật production bằng cách bỏ validator.
