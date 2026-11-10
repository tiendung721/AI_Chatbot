# ĐẶC TẢ TRIỂN KHAI CHO CODEX
# NỀN TẢNG AI CHATBOT CỔNG THÔNG TIN ĐA PHƯỜNG

**Phiên bản:** 1.0  
**Ngày lập:** 10/11/2026  
**Ngôn ngữ giao diện và tài liệu vận hành:** Tiếng Việt  
**Tên repository gợi ý:** `ai-citizen-platform`  
**Loại tài liệu:** Yêu cầu sản phẩm + kiến trúc + hợp đồng dữ liệu + kế hoạch lập trình + tiêu chí nghiệm thu.  
**Trạng thái:** Đặc tả để bắt đầu xây dựng; không phải thông báo đã có phần mềm hoặc đã kiểm thử sản xuất.

> **RÀNG BUỘC QUAN TRỌNG NHẤT:** Model, nhà cung cấp AI, API key, model dự phòng và mọi tham số kỹ thuật AI CHỈ do Developer cấu hình ở backend/hạ tầng. Admin từng phường KHÔNG được chọn, xem danh mục, thay đổi hay ghi đè model hoặc nhà cung cấp. Không có màn hình Model Selection trong Admin Portal. Chặn cả ở API, không chỉ ẩn giao diện.

> Các lựa chọn trong tài liệu này là baseline triển khai. Những con số giới hạn, thời gian lưu giữ, tải và hiệu năng được ghi là **mặc định đề xuất** không phải số liệu thực tế đã đo, cam kết SLA hay kết luận pháp lý.

---

## Mục lục

- [00. Chỉ thị thực thi dành cho Codex](#section-00)
- [01. Bối cảnh, mục tiêu và phạm vi đã chốt](#section-01)
- [02. Phân quyền và ranh giới quản trị](#section-02)
- [03. Kiến trúc và các quyết định triển khai](#section-03)
- [04. User journeys và phạm vi nghiệm thu sản phẩm](#section-04)
- [05. Cấu trúc repository và ranh giới module](#section-05)
- [06. Thiết kế giao diện và hành vi Admin Portal](#section-06)
- [07. Multi-tenancy và cách ly dữ liệu](#section-07)
- [08. Mô hình dữ liệu và ràng buộc](#section-08)
- [09. Đăng nhập, phiên người dùng và bảo vệ hồ sơ cá nhân](#section-09)
- [10. Knowledge ingestion: file, văn bản và phiên bản](#section-10)
- [11. Retrieval, evidence và câu trả lời có nguồn](#section-11)
- [12. Website synchronization](#section-12)
- [13. Draft, kiểm thử, publish và rollback](#section-13)
- [14. AI Orchestrator và OpenAI Adapter](#section-14)
- [15. Capability Registry và tính năng mở rộng](#section-15)
- [16. Actions, xác nhận và tính nhất quán giao dịch](#section-16)
- [17. Hợp đồng API ứng dụng](#section-17)
- [18. Streaming, concurrency và UX khi xảy ra lỗi](#section-18)
- [19. Bảo mật, riêng tư và các cổng chặn production](#section-19)
- [20. Cấu hình kỹ thuật chỉ dành cho Developer](#section-20)
- [21. Triển khai, lệnh chạy và vận hành](#section-21)
- [22. Usage, quota và dự toán chi phí](#section-22)
- [23. Kiểm thử bắt buộc và tiêu chí nghiệm thu](#section-23)
- [24. Dữ liệu mẫu, fixture và demo trung thực](#section-24)
- [25. Thứ tự triển khai và Definition of Done từng milestone](#section-25)
- [26. Hồ sơ bàn giao và báo cáo thực thi](#section-26)
- [27. Điều kiện không được bỏ qua khi thiếu đầu vào thực tế](#section-27)
- [28. Checklist tự rà soát trước khi Codex kết thúc](#section-28)
- [29. Prompt khởi động có thể gửi nguyên văn cho Codex](#section-29)
- [30. Nguồn kỹ thuật và cách sử dụng nguồn](#section-30)

---

<a id="section-00"></a>

## 00. Chỉ thị thực thi dành cho Codex

Bạn là kỹ sư triển khai sản phẩm này trong workspace hiện tại. Hãy **viết phần mềm chạy được**, không chỉ trả lời bằng phương án kiến trúc hoặc tạo giao diện mẫu không có backend.

### 00.1. Cách bắt đầu

1. Đọc toàn bộ file này theo từng phần nếu công cụ giới hạn dung lượng. Không suy diễn từ phần đầu rồi bỏ các ràng buộc bảo mật, test và milestone ở cuối.
2. Kiểm tra repository, `AGENTS.md`, cấu trúc hiện có, trạng thái Git và môi trường trước khi sửa. Không ghi đè hoặc xóa thay đổi của người dùng. Tôn trọng các hướng dẫn repository đang có; báo rõ xung đột cần xử lý.
3. Nếu workspace trống, khởi tạo monorepo theo mục 05. Nếu đã có mã nguồn, tái sử dụng phần phù hợp; ghi quyết định kiến trúc khi phải đổi.
4. Tạo `docs/IMPLEMENTATION_PLAN.md`, `docs/IMPLEMENTATION_STATUS.md`, `docs/DECISIONS.md`, `docs/EXTERNAL_DEPENDENCIES.md` và checklist các yêu cầu có mã định danh trong file.
5. Tạo hoặc cập nhật `AGENTS.md` ngắn gọn, trỏ tới đặc tả này và các lệnh kiểm thử. Không chép nguyên tài liệu dài này vào `AGENTS.md`. Tài liệu Codex mô tả cơ chế đọc `AGENTS.md` và giới hạn dung lượng ngữ cảnh hướng dẫn; xem [R01].
6. Sau kế hoạch ngắn, bắt đầu lập trình theo milestone. Không dừng ở việc lập kế hoạch và hỏi lại những lựa chọn đã được chốt.
7. Mọi chức năng phải nối đủ UI → API → service → database/worker → trạng thái hiển thị, không đánh dấu hoàn tất chỉ vì đã có nút hoặc route.
8. Thiếu API key, domain hay API nghiệp vụ thật: dựng interface và môi trường kiểm thử được ghi nhãn rõ; không bịa endpoint, quyền truy cập, dữ liệu hồ sơ hoặc kết quả tích hợp.
9. Không tự mở port internet, triển khai production, tạo tài nguyên tính phí, gửi tin nhắn thật, push Git hay chạy thao tác phá hủy dữ liệu ngoài phạm vi được phép.
10. Khi kết thúc một lượt làm việc, ghi rõ: đã làm gì, test nào thực sự chạy, kết quả, phần chưa xong, phụ thuộc còn thiếu và lệnh chạy tiếp. Không gọi toàn bộ sản phẩm là hoàn tất khi mới đạt một milestone.

### 00.2. Kết quả cần hướng tới

- Repository có frontend, backend, background workers, database migrations, kiểm thử và Docker.
- Hệ thống đa tenant thực sự, có ít nhất hai phường dữ liệu mẫu để kiểm tra cách ly.
- Admin phường tự cập nhật Instructions, Knowledge, nguồn website, công cụ được cấp phép, kiểm thử và xuất bản.
- Chatbot hỏi đáp dựa trên tài liệu đã xuất bản, có dẫn nguồn kiểm chứng được.
- Actions được kiểm soát bằng xác thực, phân quyền và xác nhận trước thao tác ghi.
- Tất cả Capabilities trong phạm vi có đường tích hợp thực tế; tính năng chưa được cấu hình phải báo trạng thái rõ.
- Có hướng dẫn Windows PowerShell cho phát triển và Linux Docker cho triển khai.
- Không coi local mock, dữ liệu mẫu hoặc UI đẹp là bằng chứng sẵn sàng vận hành chính thức.

### 00.3. Quy tắc chất lượng mã nguồn

TypeScript strict; Python có type hints; dữ liệu API có schema; migration có phiên bản; lỗi có mã; kiểm tra quyền ở backend. Không dùng `eval`, không thực thi code từ tài liệu upload, không bỏ xác thực để làm test chạy. Không lưu secrets trong source, log, fixture hoặc frontend bundle. Không tạo hàm rỗng trả success để vượt acceptance test.

Không tự động chạy `git reset --hard`, xóa volume, drop database, `docker compose down -v` hoặc thay đổi cấu hình hệ thống máy người dùng. Script khởi động phải không phá hủy dữ liệu.

---

<a id="section-01"></a>

## 01. Bối cảnh, mục tiêu và phạm vi đã chốt

### 01.1. Chín lựa chọn sản phẩm

| Mã | Quyết định |
|---|---|
| REQ-01 | Nhiều phường trên cùng nền tảng; mỗi phường có chatbot, cấu hình, Knowledge, hội thoại và dữ liệu độc lập. |
| REQ-02 | Công dân hỏi đáp công khai không đăng nhập; nghiệp vụ cá nhân phải xác thực. |
| REQ-03 | Knowledge nhận từ upload file, văn bản do Admin nhập và đồng bộ website. |
| REQ-04 | Hỗ trợ đầy đủ Capabilities, có kiến trúc mở rộng công cụ tùy chỉnh. |
| REQ-05 | Mỗi phường có một Admin đang hoạt động, toàn quyền nghiệp vụ trong phạm vi phường. |
| REQ-06 | Có Actions/API tra cứu và thao tác được kiểm soát. |
| REQ-07 | Hạ tầng chưa chốt nhà cung cấp; triển khai được bằng Docker trên Linux, không khóa một cloud. |
| REQ-08 | Vận hành thực tế; phải đo mức sử dụng, kiểm soát ngân sách, giám sát và sao lưu. |
| REQ-09 | Mục tiêu là bản vận hành chính thức có quản trị đầy đủ, không chỉ chatbot demo. |
| REQ-10 | Chọn/đổi model, provider, API key và tham số AI thuộc Developer duy nhất. Đây là yêu cầu đã được người dùng sửa và xác nhận. |

Các mô tả trước đây cho phép Admin phường chọn model không còn hiệu lực. Không tái sử dụng tên model, bảng giá, domain hoặc tên API chưa xác minh từ trao đổi cũ làm cấu hình mặc định.

### 01.2. Định nghĩa

- **Tenant:** một phường/đơn vị sử dụng, là ranh giới dữ liệu và quyền.
- **Assistant:** cấu hình chatbot của tenant; bản đầu có một assistant chính/tenant, schema cho phép mở rộng sau.
- **Developer/Platform Operator:** đội kỹ thuật vận hành nền tảng, không phải Admin phường.
- **Tenant Admin:** cán bộ quản trị tri thức và nội dung của một phường.
- **Knowledge:** tài liệu, bài viết, FAQ được xử lý và quản lý phiên bản.
- **Capability:** khả năng được đội kỹ thuật triển khai và cấp phép, ví dụ tìm tài liệu hoặc tìm web.
- **Action:** công cụ nghiệp vụ cụ thể, ví dụ tra cứu hồ sơ hoặc gửi phản ánh.
- **Content Release:** ảnh chụp bất biến của nội dung/cấu hình nghiệp vụ được xuất bản.
- **Runtime Profile:** cấu hình công nghệ AI do Developer quản lý, độc lập với Content Release.
- **Extension:** connector/plugin do Developer đăng ký. File PDF/DOCX/XLSX upload làm Knowledge KHÔNG phải extension có quyền chạy code.

### 01.3. Ngoài phạm vi mặc định

Không xây mô hình ngôn ngữ từ đầu; không huấn luyện lại mỗi lần tải tài liệu; không nhúng Custom GPT riêng tư từ tài khoản ChatGPT; không giả lập phiên đăng nhập ChatGPT; không tự tích hợp VNeID hay hệ thống dịch vụ công khi chưa có quyền/API. Không tự động ký, phê duyệt quyết định hành chính hoặc thanh toán thay cơ quan có thẩm quyền.

Tạo mới website cổng thông tin không thuộc phạm vi: sản phẩm cung cấp widget và trang chat độc lập để gắn vào website đang có.

---

<a id="section-02"></a>

## 02. Phân quyền và ranh giới quản trị

### 02.1. Ma trận quyền bắt buộc

| Chức năng | Developer / Operator | Admin phường | Công dân |
|---|---|---|---|
| Chọn provider, model, embedding model | Có, cấu hình máy chủ | Không | Không |
| API key, secrets, endpoint AI | Có | Không | Không |
| Model fallback, token limit, reasoning/temperature | Có | Không | Không |
| Cấp Capability, quota, connector, domain tin cậy | Có | Không tự nâng quyền | Không |
| Tạo tenant, domain mapping, cấp lại Admin | Có qua CLI vận hành | Không | Không |
| Tên chatbot, lời chào, nhận diện giao diện | Hỗ trợ khi được ủy quyền | Có, tenant của mình | Không |
| Instructions nghiệp vụ | Không sửa thường nhật | Có | Không |
| Upload/văn bản/đồng bộ Knowledge | Không truy cập mặc nhiên | Có | Không vào kho dùng chung |
| Bật/tắt Capability đã được cấp | Cấp quyền/thu hồi | Có trong phạm vi được cấp | Sử dụng nếu được phép |
| Cấu hình tham số Action cho phép | Tạo connector/schema/secrets | Có phần nghiệp vụ được cho phép | Không |
| Thử và xuất bản nội dung | Không làm thay mặc nhiên | Có | Không |
| Tra cứu thông tin cá nhân | Không mặc nhiên | Không mặc nhiên | Chỉ dữ liệu thuộc quyền của mình |
| Thực hiện thao tác ghi nghiệp vụ | Không bỏ qua kiểm soát | Chỉ theo quyền nghiệp vụ riêng | Sau xác thực và xác nhận |
| Xem model/provider trong UI hoặc API công khai/Admin | Kênh vận hành riêng | Không | Không |

Tài khoản Admin không đồng nghĩa với quyền xem mọi hồ sơ công dân. Lịch sử chat cá nhân phải được che dữ liệu theo chính sách; chức năng hỗ trợ đọc nội dung nhạy cảm cần quyền và quy trình riêng, tắt mặc định.

### 02.2. Một Admin mỗi phường

Một tài khoản Admin hoạt động tại một thời điểm cho mỗi tenant. Không cần xây quy trình nhiều người duyệt ở bản đầu. Vẫn phải có Lưu nháp → Kiểm tra → Xem thử → Xuất bản, audit và rollback.

Cho phép Developer chuyển giao Admin: vô hiệu hóa người cũ, thu hồi phiên, cấp người mới, ghi audit; không dùng chung mật khẩu. Không thêm role “editor” rồi bắt người dùng phải có người duyệt thứ hai.

MFA bắt buộc ở production. Mã khôi phục được bảo vệ; reset MFA qua quy trình vận hành có xác minh, không bằng một API public đơn giản.

### 02.3. Quyền hiệu lực phải tính tại backend

```text
effective_tools =
    tools_Developer_granted_to_tenant
  ∩ tools_enabled_in_published_release
  ∩ tools_supported_by_active_runtime
  ∩ tools_allowed_for_authenticated_principal
  ∩ tools_allowed_by_current_data_policy
  ∩ tools_with_available_budget
  - emergency_disabled_tools
```

Developer thu hồi công cụ hoặc thay đổi chính sách an toàn phải có hiệu lực cả với phiên chat đang mở. Rollback nội dung không được khôi phục quyền đã bị thu hồi.

### 02.4. Chống ghi đè model

- DTO Admin chỉ chứa các trường cho phép; cấm mass assignment.
- Trường lạ như `model`, `provider`, `api_key`, `base_url`, `temperature`, `reasoning_effort`, `runtime_profile`, `embedding_model` bị từ chối, không âm thầm bỏ qua.
- Public API và Admin API không trả model ID, provider endpoint, danh sách model hay raw provider errors.
- Instructions kiểu “chuyển sang model X” không ảnh hưởng routing.
- JSON export cấu hình Admin không được chứa cấu hình kỹ thuật/secrets.
- Preview và Publish không có tham số model. Preview luôn sử dụng Runtime Profile do Developer quy định.

---

<a id="section-03"></a>

## 03. Kiến trúc và các quyết định triển khai

### 03.1. Chọn một baseline rõ ràng

| Thành phần | Lựa chọn |
|---|---|
| Admin + trang chat + embed UI | Next.js, React, TypeScript, giao diện tiếng Việt |
| Widget loader | JavaScript/TypeScript nhỏ, tải iframe đã cách ly CSS |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database và RAG gốc | PostgreSQL 17 + pgvector + tìm kiếm từ khóa tiếng Việt |
| Background jobs | Celery, Redis; cơ chế outbox bảo đảm phát job |
| File storage | S3-compatible; MinIO dùng cho môi trường local |
| Parser | Các thư viện đọc file chuyên biệt, chạy trong worker hạn chế quyền |
| OCR | Tesseract tiếng Việt/Anh hoặc adapter OCR được Developer phê duyệt |
| AI đầu tiên | OpenAI Responses API qua SDK chính thức |
| Đổi model/provider | Interface adapter; bản đầu OpenAI thật và Mock cho test |
| HTTP/SSE | FastAPI phía sau reverse proxy; frontend cùng origin ở production |
| Reverse proxy | Nginx, TLS do môi trường triển khai cấu hình |
| Test | pytest, kiểm thử PostgreSQL thật, Playwright, kiểm thử tải |
| Packaging | Docker Compose cho local/staging; production có tài liệu HA riêng |

Node.js 24 LTS là baseline của frontend, không phải yêu cầu “phiên bản mới nhất”; tham chiếu vòng đời chính thức [R12]. Chọn và khóa exact patch/dependency/image digest tương thích khi khởi tạo; không để `latest` trong production. Ghi rõ phiên bản vào lockfile và `docs/DEPENDENCIES.md`.

**Quyết định RAG:** dùng PostgreSQL + pgvector làm mặc định để quản lý quyền, hiệu lực, thu hồi và chuyển model. Không xây đồng thời hai hệ thống RAG làm tăng độ phức tạp. OpenAI File Search chỉ là Retrieval Adapter tùy chọn sau này, không phải điều kiện để core hoạt động. File Search là một công cụ tìm kiếm hosted riêng, không đồng nhất với khả năng upload mọi loại file của ứng dụng [R06].

**Không triển khai microservices ngay:** một backend có các module nghiệp vụ, nhiều process worker từ cùng codebase. Không tạo Kubernetes, Kafka hoặc hệ thống agent tự quyết định không cần thiết ở bản đầu.

### 03.2. Sơ đồ luồng

```text
Website phường                         Admin phường
    | widget loader/iframe                 | /admin
    +----------------------+---------------+
                           |
                  Nginx / TLS / rate limit
                           |
                    FastAPI application
                           |
        +------------------+----------------------+
        | Tenant & Auth    | Assistant & Releases |
        | Chat & SSE       | Knowledge & Sources  |
        | Policy Engine    | Actions & Evaluation |
        +------------------+----------------------+
                           |
                  AI Orchestrator
                  /       |          \
       RetrievalService  AIAdapter   ActionGateway
              |             |            |
       PostgreSQL/pgvector OpenAI     Connectors được duyệt
              |
     Object storage + outbox + workers
     parse / OCR / crawl / index / eval / purge
```

### 03.3. Ba ranh giới không được trộn

1. **Control plane kỹ thuật:** cấu hình provider/model, credentials, cấp quyền, quota, provision tenant; Developer quản lý bằng file cấu hình/secret manager/CLI, không cần làm một trang model admin riêng trong bản đầu.
2. **Admin plane nghiệp vụ:** cập nhật nội dung, Knowledge, cấu hình trong hạn mức; tài khoản tenant.
3. **Citizen plane:** chat công khai và tác vụ riêng sau đăng nhập.

Đường đi dữ liệu: file gốc và chỉ mục lưu tại hạ tầng ứng dụng; chỉ đoạn cần thiết được gửi đến dịch vụ AI theo chính sách. Nếu dùng embeddings từ API ngoài, chính các đoạn văn đưa đi tạo embedding cũng là dữ liệu được gửi ra ngoài. Lưu vector nội bộ không có nghĩa toàn bộ xử lý đã ở nội bộ.

### 03.4. Đổi model sau này

ProviderAdapter chuẩn hóa hội thoại, tool requests, structured output, usage và lỗi; RetrievalService và ActionGateway độc lập provider. Model mới phải qua kiểm thử tương thích và bộ đánh giá trước khi Developer kích hoạt.

Đổi chat model không mặc nhiên phải tạo lại embeddings. Đổi embedding model/dimension/chunker thì tạo profile/chỉ mục mới, reindex, kiểm thử và chuyển index; không trộn vector khác hệ quy chiếu.

Không cam kết mọi provider hỗ trợ ngang nhau mọi công cụ hosted. Capability không tương thích phải báo rõ/khóa hoặc có adapter thay thế đã kiểm thử, không giả vờ hoạt động.

---

<a id="section-04"></a>

## 04. User journeys và phạm vi nghiệm thu sản phẩm

### 04.1. Admin đưa tri thức mới lên

Đăng nhập → chọn Knowledge → upload/soạn văn bản → kiểm tra metadata → xem nội dung trích xuất → sửa lỗi nếu cần → tạo index → Preview bản nháp → chạy bộ kiểm thử → xem diff → Xuất bản.

Chỉ xử lý file xong chưa có nghĩa đã xuất bản. Câu hỏi công dân tiếp tục dùng release cũ cho đến khi publish thành công.

### 04.2. Admin chỉnh hành vi chatbot

Sửa Instructions → lưu nháp → xem thử với tài liệu của draft → kiểm tra các giới hạn → publish. Không có model selector. Lỗi nội dung hoặc công cụ vượt quyền phải được chỉ ra cụ thể.

### 04.3. Công dân hỏi thủ tục

Mở widget → hỏi → backend xác định đúng tenant → truy xuất nguồn đang hiệu lực → trả lời tiếng Việt có nguồn → người dùng mở tài liệu/trang tham chiếu → đánh giá hữu ích.

Thiếu nguồn hoặc nguồn mâu thuẫn: nói chưa đủ thông tin, hỏi rõ phần cần thiết hoặc chỉ đến đầu mối đã được cấu hình; không bịa mức phí, hạn xử lý, số điện thoại hay văn bản.

### 04.4. Công dân tra cứu hồ sơ cá nhân

Widget đề nghị đăng nhập → mở trang chat first-party → xác thực qua IdP hợp lệ → backend gọi API theo định danh đã xác thực → kiểm tra chủ thể sở hữu hồ sơ → hiển thị dữ liệu tối thiểu.

Chỉ biết mã hồ sơ/CCCD/số điện thoại không đủ quyền truy cập. Admin phường cũng không được dùng chế độ Preview để giả làm công dân bất kỳ.

### 04.5. Công dân gửi phản ánh

Mô hình hỗ trợ soạn nháp → backend tạo đề nghị hành động → UI hiển thị chính xác nội dung, nơi nhận và dữ liệu sẽ gửi → công dân xác nhận → backend kiểm tra lại → gọi connector → hiện trạng thái và mã tiếp nhận có thật.

Không có bước xác nhận thì không được gửi. Timeout không được coi là thất bại chắc chắn để tự gửi lại.

### 04.6. Thu hồi khẩn cấp

Admin thu hồi tài liệu sai → dữ liệu không còn được dùng ở lượt truy xuất mới → cache liên quan mất hiệu lực → câu trả lời đang tạo được kiểm tra lại trước khi phát hành → lịch sử có nguồn bị thu hồi được gắn cảnh báo phù hợp. Không hứa thu hồi các bản đã được người dùng chụp/copy ra ngoài.


<a id="section-05"></a>

## 05. Cấu trúc repository và ranh giới module

```text
ai-citizen-platform/
  AGENTS.md
  README.md
  CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md
  package.json
  pnpm-workspace.yaml
  pnpm-lock.yaml
  .env.example
  .gitignore
  compose.yaml
  compose.production.example.yaml
  apps/
    web/                         # Next.js: /admin, /chat, /embed
    widget-loader/               # build ra widget.js
    api/
      pyproject.toml
      uv.lock
      alembic.ini
      migrations/
      src/citizen_ai/
        main.py
        config.py
        cli.py
        common/                  # errors, ids, pagination, clock
        auth/                    # admin sessions, MFA, OIDC
        tenancy/                 # TenantContext, directory, RLS
        assistants/              # drafts, content releases
        knowledge/               # documents, versions, metadata
        retrieval/               # lexical, vectors, ranking, evidence
        ingestion/               # file parsers, antivirus, OCR
        website_sync/            # safe fetch, diff, scheduling
        chat/                    # sessions, turns, events, ownership
        ai/
          contracts.py
          orchestrator.py
          prompts.py
          adapters/
            openai_responses.py
            mock.py
          runtime_profiles.py
        capabilities/            # registry, compatibility, grants
        actions/                 # proposals, confirm, execution
        connectors/              # vetted application connectors
        releases/                # publish/rollback/revalidation
        evaluations/             # datasets, runs, thresholds
        usage/                   # budgets, cost reconciliation
        audit/                   # append-only events, redaction
        storage/                 # S3, signed downloads, cleanup
        workers/                 # Celery tasks, outbox dispatcher
        ops/                     # technical CLI; no public model API
      tests/
        unit/
        integration/
        isolation/
        security/
        provider_contracts/
  packages/
    api-client/                  # generated types từ OpenAPI
    ui/                          # components dùng chung
  fixtures/
    tenants/
    knowledge/
    connectors/
    evaluation/
    crawler-site/                # website giả lập để test đồng bộ
  tests/
    e2e/
    load/
  infrastructure/
    docker/
    nginx/
    monitoring/
  scripts/
    bootstrap.ps1
    dev.ps1
    check.ps1
    bootstrap.sh
    dev.sh
    check.sh
  docs/
    ARCHITECTURE.md
    DECISIONS.md
    DATABASE.md
    SECURITY.md
    API.md
    ADMIN_GUIDE.md
    DEPLOYMENT.md
    OPERATIONS.md
    EXTERNAL_DEPENDENCIES.md
    IMPLEMENTATION_PLAN.md
    IMPLEMENTATION_STATUS.md
    TEST_REPORT.md
    DEPENDENCIES.md
```

Một Python package dùng chung cho API và worker. Không tạo một bản sao logic parse/retrieval/actions trong frontend hoặc worker riêng. Source tree có thể điều chỉnh nhỏ khi có lý do, nhưng không làm mờ ranh giới quyền.

Dùng `pnpm` workspace và `uv` cho Python; khóa phiên bản trình quản lý. Docker phải tự cài dependency của image, không bắt máy người dùng cài toàn bộ công cụ để chạy compose.

---

<a id="section-06"></a>

## 06. Thiết kế giao diện và hành vi Admin Portal

### 06.1. Yêu cầu chung

Thiết kế light enterprise: rõ ràng, nhiều khoảng trắng, dễ thao tác cho cán bộ không biết lập trình. Giao diện tiếng Việt đầy đủ dấu; cùng font, khoảng cách và thành phần giữa các màn. Không dùng placeholder “Lorem ipsum” trong bản bàn giao.

Sidebar có tên phường cố định theo tài khoản; không có tenant switcher cho Admin một phường. Luôn hiển thị trạng thái “Bản nháp”, “Đang hoạt động”, “Có thay đổi chưa xuất bản”. Loading/empty/error/success/permission-denied đều phải có UI thực.

Không có menu Model, Provider, API Key, Temperature, Reasoning hay Advanced AI Settings. Không vô tình lộ các mục đó qua trang analytics, debug, export, playground hoặc developer tools trong response JSON.

### 06.2. Danh mục màn hình

| ID | Màn hình | Nội dung và thao tác |
|---|---|---|
| UI-01 | Đăng nhập và MFA | Login, TOTP, hết phiên, đổi mật khẩu, recovery theo quyền |
| UI-02 | Dashboard | Lượt hỏi, phản hồi, tài liệu lỗi, job đang chạy, release hiện hành |
| UI-03 | Cấu hình chatbot | Tên, mô tả, Instructions, lời chào, câu gợi ý, đầu mối hỗ trợ |
| UI-04 | Knowledge | Danh sách tài liệu, nguồn, trạng thái xử lý, public approval, phiên bản |
| UI-05 | Chi tiết tài liệu | Metadata, trích xuất theo trang/sheet, lỗi OCR, lịch sử, thu hồi |
| UI-06 | Soạn tri thức | FAQ/văn bản, rich text giới hạn, xem trước, lịch sử |
| UI-07 | Nguồn website | Domain được cấp, URL/phạm vi crawl, lịch, diff, lỗi đồng bộ |
| UI-08 | Capabilities | Bật/tắt trong phạm vi cấp phép; trạng thái, quyền, giới hạn |
| UI-09 | Actions | Danh mục được cấp; tham số nghiệp vụ cho phép; kết nối; test an toàn |
| UI-10 | Playground | Chat draft, nguồn thật, trace đã làm sạch, không có model selector |
| UI-11 | Kiểm thử | Bộ câu hỏi, đáp án/kỳ vọng, lần chạy, lỗi và so sánh |
| UI-12 | Xuất bản/Phiên bản | Diff, readiness checks, publish, rollback, lý do |
| UI-13 | Hội thoại | Bộ lọc thời gian/trạng thái, phản hồi, riêng tư và redaction |
| UI-14 | Thống kê sử dụng | Tổng request, chất lượng, quota còn lại; không hiện model/provider |
| UI-15 | Giao diện & Nhúng | Logo, màu hợp lệ, lời chào, copy embed code, preview mobile |
| UI-16 | Bảo mật tài khoản | Phiên đăng nhập, MFA, đăng xuất tất cả, lịch sử thay đổi |

Không cho nhập tùy ý JavaScript/CSS/HTML vào giao diện. Branding phải dùng schema màu, logo và text đã kiểm tra. Logo SVG cần sanitizer đáng tin hoặc chỉ chấp nhận ảnh raster.

### 06.3. Bố cục Configure giống tinh thần Custom GPT Builder

Desktop chia hai cột: cấu hình bên trái, Preview bên phải. Các nhóm: Thông tin → Instructions → Knowledge → Capabilities → Actions. Nút “Lưu nháp”, “Kiểm tra”, “Xuất bản” rõ ràng, không gộp thành một nút Save âm thầm ảnh hưởng công dân.

Instructions có độ dài tối đa được backend áp đặt; lưu có version, cảnh báo thay đổi chưa lưu. Chỉ đây là ô văn bản; quyền backend không được chuyển thành các câu hướng dẫn có thể sửa.

### 06.4. Danh sách Knowledge

Mỗi dòng có tên tài liệu, loại file, nguồn, số trang/sheet đã đọc, trạng thái, phiên bản, ngày cập nhật, hiệu lực, nhãn “Đã xác nhận công khai”, đang nằm trong release nào.

Upload nhiều file trả kết quả từng file. Một file lỗi không làm các file khác bị ghi là thành công hoặc mất trạng thái. Có retry một job; retry idempotent, không tạo trùng chunk.

### 06.5. Playground và trace

Hiển thị: intent phân loại, nguồn đã tìm, đoạn tham chiếu, tool đã chạy, thời gian và cảnh báo. Không hiển thị chain-of-thought, credentials, raw prompt cốt lõi hoặc raw response có trường model.

Preview có nhãn bản nháp, không gọi Action ghi thật. Test connector ghi chỉ trong sandbox có dữ liệu giả, không dùng tài khoản công dân thật để “thử nút”.

### 06.6. UI widget

Có mở/đóng, toàn màn hình điện thoại, câu gợi ý, gõ câu hỏi, nguồn dạng thẻ, nút đánh giá, thông báo lỗi và tải lại lượt an toàn. Có nút “Đăng nhập để tra cứu hồ sơ” mở trang first-party. Hỗ trợ bàn phím, focus, screen reader, tương phản phù hợp; đánh giá accessibility trước nghiệm thu.

Nguồn có loại rõ: “Tài liệu của phường”, “Trang chính thức”, “Tài liệu bạn gửi”. Không trình bày tài liệu cá nhân upload như nguồn pháp lý chính thức.

---

<a id="section-07"></a>

## 07. Multi-tenancy và cách ly dữ liệu

### 07.1. Xác định tenant

Anonymous request dùng assistant public key để tra directory phía server. Public key là định danh công khai, không phải secret. Tenant của resource được backend xác định, không lấy tùy ý từ body.

Admin tenant lấy từ session đã xác thực. Citizen dùng tenant gắn với chat session, kết hợp danh tính từ token/phiên hợp lệ. Kiểm tra quan hệ giữa principal, tenant, resource và action trên từng request.

Directory public chỉ trả dữ liệu tối thiểu cần dựng widget. Không dùng truy vấn không có tenant để quét bảng hội thoại/tài liệu.

### 07.2. Cách ly PostgreSQL

Tất cả bảng tenant-owned có `tenant_id NOT NULL`; dùng composite foreign key `(tenant_id, resource_id)` khi liên kết tài nguyên tenant để ngăn gắn tài liệu phường B vào release phường A.

Bật RLS, có cả `USING` và `WITH CHECK`; runtime role không là superuser, không có `BYPASSRLS`, không là migration/table-owner role. RLS của PostgreSQL có các ngoại lệ cho owner/superuser, nên không được chỉ tạo policy rồi dùng tài khoản database quyền cao [R10].

Ví dụ nguyên tắc SQL, Codex phải viết migration và test thực tế:

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_documents_policy ON documents
USING (
  tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
)
WITH CHECK (
  tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
);
```

Đặt context bằng tham số an toàn trong transaction:

```sql
SELECT set_config('app.tenant_id', :trusted_tenant_id, true);
```

`trusted_tenant_id` đến từ TenantContext đã xác thực, không nối chuỗi request vào SQL. Thiếu context phải default-deny. Chỉ dùng transaction-local setting để không rò context qua connection pool. Streaming không giữ một transaction/database connection mở suốt lời gọi AI.

Worker cũng phải thiết lập TenantContext trước truy cập DB. Job payload chỉ mang IDs, không chứa token/secrets/nội dung cá nhân không cần thiết. Worker kiểm tra lại quyền và trạng thái của tài nguyên khi chạy.

### 07.3. Cách ly ngoài database

- Object key: `tenant/{tenant_uuid}/documents/{version_uuid}/...`; bucket private.
- Cache: key chứa tenant, release, security/revocation epoch, embedding profile và scope truy cập.
- Không cache chung câu trả lời cá nhân hoặc nội dung attachment.
- Redis job/event stream, SSE reconnect, vector search, citation endpoint đều kiểm tra tenant/owner.
- Source URL/file ID do model đưa ra không được truy cập nếu không nằm trong evidence set đã cấp.
- Không deduplicate public API theo checksum xuyên tenant làm lộ sự tồn tại tài liệu của đơn vị khác.
- Export, backup restore, audit search và test datasets cũng thuộc ranh giới tenant.

### 07.4. Domain và widget không phải cơ chế xác thực

CSP `frame-ancestors` theo allowlist kiểm soát nhúng. CORS/Origin/domain allowlist không chứng minh danh tính công dân và không bảo vệ API public khỏi mọi script gọi trực tiếp.

Khi dùng iframe cross-origin, Origin của request bên trong thường là chatbot origin, không phải website mẹ. Không xây kiểm soát tenant dựa trên giả định ngược lại. `postMessage` phải kiểm tra `origin`, `source` và schema; không dùng `*` cho dữ liệu nhạy cảm.

---

<a id="section-08"></a>

## 08. Mô hình dữ liệu và ràng buộc

### 08.1. Quy ước

UUID cho ID; `timestamptz` lưu UTC; hiển thị `Asia/Ho_Chi_Minh`. Tiền/chi phí dùng Decimal, không float. Mọi entity cần `created_at`, `updated_at`, version/optimistic locking nếu sửa đồng thời. Tên trường code tiếng Anh, nhãn UI tiếng Việt.

Không dùng soft delete như cơ chế xóa dữ liệu duy nhất: phải có purge workflow xử lý bytes, chunks, vector, cache và bản lưu ở provider nếu có.

### 08.2. Bảng cốt lõi

| Bảng | Các trường/ràng buộc chính |
|---|---|
| `tenants` | id, slug unique, display_name, status, timezone, security_epoch |
| `tenant_domains` | tenant_id, hostname, kind, verified_at; domain do Developer xác nhận |
| `tenant_admin_memberships` | tenant_id, account_id, status; unique partial một admin active/tenant |
| `accounts` | id, email/username, password_hash hoặc external identity; không trộn secrets vào profile |
| `admin_sessions` | hashed_session_token, account_id, tenant_id, expires_at, revoked_at |
| `mfa_credentials` | account_id, encrypted_secret, recovery_hashes, enabled_at |
| `citizen_identities` | tenant_id, issuer, subject, verified claims tối thiểu; unique theo issuer/subject/tenant |
| `assistants` | tenant_id, id, public_key unique, active_release_id, paused |
| `assistant_drafts` | tenant_id, assistant_id, revision, config_json, updated_by |
| `content_releases` | tenant_id, assistant_id, sequence, immutable snapshot, hash, created_by, reason |
| `release_documents` | tenant_id, release_id, document_version_id; composite FKs |
| `release_tool_bindings` | tenant_id, release_id, tool_version_id, business_config_snapshot |
| `knowledge_sources` | tenant_id, type=file/text/website, label, status |
| `documents` | tenant_id, id, source_id, title, latest_version_id, revoked_at |
| `document_versions` | tenant_id, document_id, number, object_key, sha256, parse_status, metadata_json |
| `document_sections` | tenant_id, version_id, locator_json, extracted_text, extraction_warnings |
| `knowledge_chunks` | tenant_id, version_id, section_id, ordinal, text, normalized_text, checksum |
| `embedding_profiles` | Developer-managed: provider/model fingerprint, dimensions, metric, chunker_version |
| `chunk_embeddings` | tenant_id, chunk_id, embedding_profile_id, embedding; unique chunk/profile |
| `ingestion_jobs` | tenant_id, version_id, status, attempt, progress, error_code |
| `website_sources` | tenant_id, approved_domain_id, seed_urls, rules_json, schedule, status |
| `website_pages` | tenant_id, source_id, canonical_url, etag, content_hash, last_success_at |
| `sync_runs` | tenant_id, source_id, counts, failures, started_at, finished_at |
| `capability_grants` | tenant_id, capability_id, Developer-approved limits, enabled_by_operator |
| `tool_definitions` | global vetted catalog: id, version, input_schema, risk, connector_ref |
| `tenant_tool_bindings` | tenant_id, tool_version_id, approved business_config, granted |
| `action_proposals` | tenant_id, principal_id, action_version, payload, payload_hash, nonce_hash, expiry, state |
| `action_executions` | tenant_id, proposal_id, idempotency_key, state, upstream_reference, sanitized_result |
| `chat_sessions` | tenant_id, assistant_id, mode, owner_id/token_hash, pinned_release_id, expires_at |
| `chat_turns` | tenant_id, session_id, client_request_id, state, release_id, technical runtime fingerprint |
| `chat_messages` | tenant_id, session_id, role, content, structured_answer, privacy_class, purge_at |
| `session_attachments` | tenant_id, session_id, owner_scope, object_key, scan_state, purge_at |
| `citations` | tenant_id, turn_id, evidence_id, source_type, exact version/locator |
| `feedback` | tenant_id, turn_id, actor_scope, rating, optional comment |
| `evaluation_cases` | tenant_id, dataset_version, question, expected_evidence, expected_behavior |
| `evaluation_runs` | tenant_id, draft_hash/release_id, runtime_fingerprint, results, status |
| `usage_events` | tenant_id, turn/job/action_id, technical usage, price_snapshot_id, cost_status |
| `budget_reservations` | tenant_id, operation_id unique, reserved_amount, actual_amount, expiry, state |
| `audit_events` | tenant_id nullable cho global ops, actor, event_type, resource, redacted diff, request_id |
| `outbox_events` | tenant_id, event_id, type, payload_ids, status, attempts, next_attempt_at |
| `deletion_jobs` | tenant_id, target, scope, status, external_deletions, completed_at |

Global tool definitions, embedding profiles và pricing catalog chỉ Developer được sửa. Admin serialization không lấy trực tiếp ORM object ra JSON.

### 08.3. Index và constraints

Bắt buộc unique `(tenant_id, session_id, client_request_id)` chống tạo lại turn; unique `(tenant_id, principal_id, idempotency_key)` cho thao tác ghi. Cùng idempotency key nhưng payload khác trả conflict.

Index `(tenant_id, status, created_at)`, `(tenant_id, document_id, version_number)`, `(tenant_id, session_id, created_at)`, source canonical URL theo tenant. Dùng CHECK cho trạng thái hoặc enum migrations rõ ràng.

Publication release immutable. Nếu cần sửa thì tạo release mới, không UPDATE ngầm JSON của release cũ.

### 08.4. Vector storage

Lưu `embedding_profile_id` cùng mỗi vector; kiểm tra dimensions tại ingestion và query. Bản đầu có thể dùng cột `vector` không cố định chiều và exact search trong tập đã lọc đúng tenant/profile/release; không tính khoảng cách giữa các profile khác nhau.

Khi dùng HNSW/IVFFlat, tạo index cho chiều/profile tương thích và benchmark có filter tenant. Approximate indexing có thể trả thiếu kết quả sau filter; pgvector hướng dẫn iterative scans và các cách xử lý [R11]. Không giải quyết thiếu kết quả bằng cách bỏ filter quyền.

Không khẳng định exact search đáp ứng mọi quy mô; đưa ANN optimization vào load-test milestone khi số chunk tăng.

---

<a id="section-09"></a>

## 09. Đăng nhập, phiên người dùng và bảo vệ hồ sơ cá nhân

### 09.1. Admin

Dùng server-side session, cookie HttpOnly/Secure/SameSite phù hợp, CSRF cho request ghi và kiểm tra Origin ở route liên quan. Password hash bằng thư viện Argon2id được duy trì; rate-limit đăng nhập và kiểm soát brute force. Không tự viết thuật toán password hash.

Có idle timeout, absolute timeout, revoke-all-sessions, đổi mật khẩu và bắt buộc MFA production. Đăng nhập thất bại không làm lộ account có tồn tại.

Developer provision tenant/admin bằng CLI an toàn. Không seed mật khẩu dùng chung trong code. Local bootstrap sinh mật khẩu một lần hoặc yêu cầu nhập, lưu ngoài Git, yêu cầu đổi; production không tạo tài khoản demo.

### 09.2. Anonymous chat

Tạo session token ngẫu nhiên đủ mạnh, lưu bản hash phía server; token chỉ cho phép truy cập đúng session và tenant. ID UUID không thay thế secret session token.

Widget iframe giữ token trong bộ nhớ; không đặt token trong URL, analytics hoặc log. Không dùng localStorage cho token hồ sơ cá nhân. Khi reload, cho phép bắt đầu phiên anonymous mới nếu không có cơ chế resume an toàn đã kiểm thử.

Anonymous sessions không có tool cá nhân. Upload của anonymous tắt mặc định; chỉ được bật theo Developer policy cho dữ liệu công khai, giới hạn nhỏ và có cảnh báo.

### 09.3. Citizen authentication

Chuẩn bị adapter OIDC với thư viện đã được kiểm tra: Authorization Code + PKCE, state, nonce, kiểm tra issuer/audience/signature/expiry và redirect URI allowlist. Không tin header `X-User-Id` do browser gửi.

Nhà cung cấp thật chưa được xác định. Chạy local với IdP thử nghiệm hoặc identity fixture trong test harness; production phải từ chối mock identity. Giao diện production hiển thị “Chức năng đăng nhập chưa được đơn vị cấu hình” nếu chưa có IdP, không báo đã đăng nhập giả.

Không mặc định tích hợp VNeID. Khi API/IdP thật được cấp, thêm connector và contract tests theo tài liệu chính thức của hệ thống đó.

### 09.4. Iframe và đăng nhập

Bản đầu: hỏi đáp công khai hoạt động trong iframe; nghiệp vụ cá nhân chuyển sang trang `/chat/{assistant_public_key}` ở top-level, đăng nhập first-party. Không phụ thuộc third-party cookies để chạy nghiệp vụ cá nhân.

Tạo phiên authenticated mới sau login. Không tự gộp lịch sử anonymous với hồ sơ công dân. Chuyển lịch sử cần consent và cơ chế transfer code một lần, chỉ bổ sung khi có test an toàn.

### 09.5. Kiểm tra chủ thể

ActionGateway lấy `subject` và tenant từ context máy chủ. Connector phải kiểm tra hồ sơ thuộc subject hoặc có ủy quyền hợp lệ trước khi trả dữ liệu. Mã hồ sơ là điều kiện tra cứu, không phải chứng cứ sở hữu.

Không đưa access token, CCCD đầy đủ, địa chỉ hoặc hồ sơ đầy đủ vào prompt khi chỉ cần trạng thái. Ưu tiên UI thẻ dữ liệu server-rendered cho trường nhạy cảm; model chỉ nhận phần đã giảm thiểu và được phê duyệt.


<a id="section-10"></a>

## 10. Knowledge ingestion: file, văn bản và phiên bản

### 10.1. Các định dạng cần hỗ trợ

| Định dạng | Xử lý bắt buộc |
|---|---|
| PDF có text | Đọc toàn bộ trang, giữ số trang vật lý, tiêu đề, bảng và cảnh báo trích xuất |
| PDF scan | OCR `vie+eng` theo trang cần OCR; có trạng thái chất lượng và review |
| DOCX | Đoạn, heading, bảng, header/footer liên quan; locator theo mục, không bịa số trang |
| XLSX | Đọc mọi sheet được chọn rõ, giữ tiêu đề cột, dòng, vùng ô, merged cells |
| PPTX | Đọc từng slide, text và bảng; locator theo slide |
| TXT/MD | Chuẩn hóa encoding, giữ heading/đoạn |
| CSV | Phát hiện/cho chọn delimiter và encoding, giữ cột và dòng |
| HTML | Sanitize, lấy nội dung chính, không thực thi script |
| PNG/JPG | OCR nếu capability/chính sách cho phép; không coi mô tả ảnh là văn bản pháp lý |

File `.doc`, `.xls`, `.xlsm`, file nén, executable và định dạng chưa hỗ trợ phải được từ chối rõ hoặc yêu cầu chuyển đổi. Không nhận rồi trả “đã xử lý” với nội dung rỗng. Không chạy macro, công thức hay external links của Office.

Các file Knowledge do hệ thống xử lý riêng rồi lập chỉ mục; không giả định OpenAI File Search hỗ trợ trực tiếp mọi định dạng trong bảng [R06].

### 10.2. Mặc định giới hạn kỹ thuật đề xuất

- 25 MB/file; 10 file/lượt upload.
- PDF tối đa 300 trang/file; ảnh tối đa 25 megapixel.
- XLSX tối đa tổng 100.000 dòng và 100 sheet/file.
- Văn bản trích xuất có giới hạn bytes/tokens/job để ngăn decompression bomb.
- Worker có timeout CPU/RAM và số job đồng thời riêng cho OCR.
- Vượt giới hạn thì fail với thông báo và gợi ý chia file; không âm thầm cắt bớt rồi publish.
- Mọi giới hạn do Developer cấu hình; Admin chỉ nhìn thấy và không tự tăng.

Các giá trị này là baseline để phát triển, phải điều chỉnh sau thử tải/tài liệu thực tế.

### 10.3. Pipeline trạng thái

```text
uploaded
  -> scanning
  -> extracting
  -> needs_review (nếu thiếu text, OCR thấp, metadata mâu thuẫn)
  -> indexing
  -> ready
```

Nhánh lỗi: `quarantined`, `failed`, `cancelled`. Thu hồi là cờ/trạng thái độc lập áp dụng cả khi đã ready. Publication nằm ở release membership, không dùng `ready == published`.

Quy trình:

1. Tạo document version và object key riêng tenant.
2. Validate extension + MIME/magic bytes + kích thước thực.
3. File vào vùng quarantine private, quét mã độc.
4. Worker parse toàn bộ phạm vi được chấp nhận; mỗi trang/sheet có kết quả hoặc lỗi.
5. Chuẩn hóa Unicode, bỏ nội dung điều hướng lặp có kiểm soát; bảo toàn chữ có dấu.
6. Lưu extraction warnings và locator.
7. Admin review nếu cần; sửa nội dung trích xuất phải tạo revision/audit, không thay file gốc.
8. Chunk theo cấu trúc, gắn metadata.
9. Tạo embeddings bằng profile do Developer chọn.
10. Lưu chunks/vectors, đánh dấu ready khi transaction hoàn tất.
11. Đưa vào draft selection; chỉ release được publish mới dùng cho công dân.

Dùng job IDs bền vững và outbox. Celery retry không được tạo duplicate document version/chunk. Retry sau worker crash phải tiếp tục hoặc xử lý lại idempotent.

### 10.4. Quy tắc cho Excel

Phân biệt giá trị ô, công thức và cached value. Không tự tính công thức không đáng tin. Khi không có cached value, giữ cảnh báo và công thức dưới dạng dữ liệu; không bịa kết quả.

Không nối các hàng thành text mất tiêu đề cột. Mỗi chunk bảng phải chứa tên sheet, header, row range, đơn vị và context của bảng. Dòng có nội dung nối nhiều ô phải bảo toàn quan hệ.

Liệt kê cả sheet ẩn và cảnh báo cho Admin; không âm thầm bỏ sheet hoặc mặc định công bố nội dung ẩn. Admin xác nhận phạm vi sheet trước publish. Lưu quyết định vào metadata/version.

### 10.5. Metadata tài liệu

```json
{
  "title": "Hướng dẫn minh họa",
  "document_number": null,
  "issued_by": null,
  "issued_at": null,
  "effective_from": null,
  "effective_to": null,
  "authority_level": "local_guidance",
  "jurisdiction": "current_tenant",
  "source_url": null,
  "visibility": "admin_only",
  "approved_for_public": false,
  "allow_public_download": false,
  "supersedes_version_id": null,
  "topic_tags": [],
  "review_notes": null
}
```

Đây là schema nội bộ minh họa; thêm validators và enum chính thức. Ngày không xác định phải là null, không lấy ngày upload làm ngày hiệu lực.

Admin có thể sửa metadata, nhưng không được tự đặt `tenant_id`, model, embedding profile, secret hay quyền vượt policy. Public approval cần thao tác rõ ràng, có cảnh báo tài liệu chứa dữ liệu cá nhân.

### 10.6. Văn bản nhập trực tiếp

Editor hỗ trợ heading, paragraph, list, table, link an toàn; lưu canonical Markdown hoặc JSON có schema. Cấm HTML script/embed.

FAQ gồm câu hỏi, đáp án, nguồn căn cứ và ngày hiệu lực nếu có. FAQ không trở thành nguồn có thẩm quyền cao hơn văn bản chính thức chỉ vì được nhập mới hơn.

### 10.7. Xóa và thu hồi

“Thu hồi ngay” là chặn sử dụng cho câu trả lời mới, cập nhật security epoch và cache; “Xóa vĩnh viễn” là workflow riêng xử lý dữ liệu và thời hạn lưu giữ.

Release cũ giữ bằng chứng version IDs nhưng không được phục hồi quyền dùng tài liệu bị thu hồi. Khi xóa pháp lý/bảo mật cần purge nội dung gốc, index, provider copies và cache theo chính sách; audit chỉ giữ metadata tối thiểu được phép.

---

<a id="section-11"></a>

## 11. Retrieval, evidence và câu trả lời có nguồn

### 11.1. RetrievalRequest

```text
trusted tenant_id
principal scope
active content_release_id hoặc draft snapshot đã xác thực
question
as_of timestamp từ server
embedding_profile_id từ Runtime Profile
required visibility/public approval
current security_epoch
max evidence/token budget
```

Không có API public nhận tự do `vector_store_id`, `tenant_id`, SQL filters hoặc document IDs rồi truy xuất.

### 11.2. Quy trình tìm kiếm

1. Xác định phạm vi tài liệu trước retrieval: đúng tenant, release, đã được duyệt công khai, không thu hồi, đúng hiệu lực.
2. Chuẩn hóa query cho tìm từ khóa: Unicode, không dấu và mapping `đ`/`d`; giữ phiên bản gốc để model hiểu.
3. Tìm kiếm lexical (PostgreSQL `simple`/unaccent hoặc chiến lược tương thích tiếng Việt) kết hợp pgvector.
4. Hợp nhất kết quả bằng rank fusion; cấu hình khởi điểm top 20 mỗi nhánh, tối đa 6–8 evidence blocks sau rerank.
5. Ưu tiên phù hợp hiệu lực, thẩm quyền, địa bàn và loại nguồn; không chỉ ngày đăng mới nhất.
6. Khử trùng, bổ sung heading/bảng liền kề nhưng không vượt ACL.
7. Tạo evidence IDs máy chủ, ví dụ `E1`, `E2`; lưu quan hệ với document version/chunk/locator.
8. Không có đủ evidence thì trả trạng thái thiếu nguồn hoặc cần hỏi rõ. Không lấy điểm cosine tùy tiện làm “độ tin cậy 95%”.

Chunk khởi điểm khoảng 600–900 tokens, overlap 80–120 tokens là cấu hình thử nghiệm; ưu tiên ranh giới mục/bảng thay vì cắt cứng. Phải đo retrieval trên bộ dữ liệu tiếng Việt.

### 11.3. Hiệu lực và mâu thuẫn

Chỉ những ngày/quan hệ thay thế đã được xác nhận mới dùng làm bộ lọc pháp lý. Nếu metadata chưa rõ, gắn cờ cần review. Không tự suy đoán ngày hết hiệu lực từ tên file.

Hai nguồn có nội dung trái nhau nhưng chưa xác định căn cứ áp dụng: không tự chọn nguồn có score cao nhất và trả lời chắc chắn. Hiển thị điểm chưa rõ, nguồn liên quan và đầu mối xác minh.

Thông tin hồ sơ động, lịch hẹn còn chỗ hoặc kết quả xử lý phải dùng Action/API, không suy diễn từ tài liệu tĩnh.

### 11.4. Evidence object phía backend

```json
{
  "evidence_id": "E1",
  "source_type": "knowledge",
  "document_version_id": "uuid-do-server-cap",
  "title": "Tài liệu minh họa",
  "locator": {
    "kind": "pdf_page",
    "page_start": 2,
    "page_end": 2,
    "sheet": null,
    "cell_range": null,
    "section": null
  },
  "text": "Đoạn nội dung thực sự được truy xuất",
  "source_url": null,
  "effective_from": null,
  "retrieved_at": "server_timestamp"
}
```

Evidence được xem là dữ liệu không đáng tin về mặt instruction. Bất kỳ đoạn “bỏ qua quy tắc” nào bên trong không có quyền điều khiển backend.

### 11.5. AnswerPacket và kiểm tra nguồn

Mô hình tạo cấu trúc với các đoạn trả lời và danh sách evidence IDs tham chiếu. Backend tự bổ sung tên tài liệu, URL và locator từ evidence set.

```json
{
  "status": "answered",
  "blocks": [
    {
      "text": "Nội dung trả lời dựa trên đoạn nguồn.",
      "evidence_ids": ["E1"]
    }
  ],
  "follow_up_question": null,
  "needs_login": false
}
```

Các trạng thái: `answered`, `needs_clarification`, `insufficient_evidence`, `conflicting_sources`, `needs_login`, `action_confirmation`, `temporarily_unavailable`.

Validator kiểm tra schema, ID thuộc evidence set, nguồn còn truy cập được, không thu hồi giữa lúc generate, và các trường bắt buộc. Structured Outputs giúp định dạng đúng schema nhưng không bảo đảm nội dung đúng; vẫn cần xử lý refusal/incomplete và kiểm thử tính bám nguồn [R04].

Không cho model tự tạo URL/số trang nguồn tùy ý. Tài liệu DOCX không có pagination chuẩn không được hiển thị “trang 7” giả; dùng tiêu đề mục. XLSX dùng sheet và vùng dòng/ô.

Kiểm tra tồn tại citation không tương đương kiểm tra toàn bộ câu đã được chứng minh. Đánh giá bám nguồn bằng test, human review và những kiểm tra số liệu trọng yếu; không quảng cáo “AI chính xác tuyệt đối”.

### 11.6. Lịch sử và tài liệu bị thu hồi

Câu trả lời về thủ tục phải truy xuất lại theo release hiện hành, không chỉ dựa vào câu trả lời cũ trong lịch sử. Summary/history có nguồn bị thu hồi phải được đánh dấu không còn đáng tin hoặc loại khỏi context liên quan.

Không phục hồi tài liệu đã thu hồi chỉ vì đang có câu trả lời cũ trong session. Security policy hiện tại luôn thắng content snapshot cũ.

### 11.7. Public source viewer

Route nguồn kiểm tra release/evidence được phép công khai, không cung cấp object-storage URL tùy ý. Public download toàn bộ file chỉ khi `allow_public_download=true` và source được duyệt.

Nội dung source viewer được sanitize. Link web mở an toàn, không cho `javascript:`, `file:` hoặc host không được duyệt.

---

<a id="section-12"></a>

## 12. Website synchronization

### 12.1. Nguồn và lịch

Admin chọn domain trong danh sách Developer đã cấp cho tenant, thêm sitemap/RSS/URL bắt đầu và đường dẫn include/exclude. Không mặc định website nào đó thuộc phường hay có CMS API.

Có manual sync, lịch theo múi giờ, pause/resume, xem lần thành công cuối, số bài mới/sửa/mất và lỗi từng URL. Mặc định đề xuất mỗi 6 giờ; không crawl toàn site vô hạn.

Thứ tự connector: CMS API chính thức khi được cung cấp → RSS/sitemap → HTML có bộ chọn nội dung. Browser rendering chỉ thêm khi cần, trong worker riêng đã giới hạn; không yêu cầu bypass cơ chế bảo vệ website.

### 12.2. Safe fetch bắt buộc

Validate scheme/host/port, DNS và IP đích; chặn loopback, link-local, metadata endpoints, mạng private với crawler công khai. Kiểm tra lại redirect và kết nối; tránh tình trạng kiểm DNS một lần rồi HTTP client resolve lại địa chỉ khác. OWASP mô tả rủi ro SSRF và DNS rebinding này [R13].

Domain allowlist phải match theo hostname đã normalize/punycode, không dùng `endswith("gov.vn")` tùy tiện. Chặn URL có userinfo, không cho query chứa token bí mật, giới hạn số redirect, bytes tải về và timeout.

Connector nghiệp vụ được Developer phê duyệt có thể gọi private endpoint theo egress rule riêng; không mở quyền đó cho crawler hoặc URL Admin nhập.

### 12.3. Đồng bộ và phiên bản

Canonicalize URL trong phạm vi đã cấp. Sử dụng ETag/Last-Modified nếu có, content hash làm căn cứ phát hiện thay đổi. Lưu raw snapshot tối thiểu được phép và nội dung chính đã làm sạch.

Một nội dung sửa tạo document version mới, không overwrite version đang publish. Mặc định các thay đổi chờ Admin review/publish. Không tự công bố chỉ vì nguồn vừa đăng.

Lỗi mạng/403 không đồng nghĩa bài đã bị xóa. Trường hợp 404/410 lặp lại theo policy tạo cảnh báo/tombstone; không xóa hàng loạt Knowledge vì một lần website lỗi.

Tôn trọng quyền thu thập và giới hạn tải; không coi robots.txt là bằng chứng đủ về quyền sử dụng dữ liệu. Lịch crawler có lock để không chạy chồng cùng source.

### 12.4. Trace và kiểm thử

Hiển thị diff nội dung, URL gốc, thời điểm crawl, ngày đăng nếu xác minh được, trạng thái chuẩn hóa. Website fixture trong repo phải có bài mới, bài sửa, redirect, bài xóa, menu lặp và nội dung prompt injection để test.

---

<a id="section-13"></a>

## 13. Draft, kiểm thử, publish và rollback

### 13.1. Hai version độc lập

**Content Release** thuộc Admin: Instructions, branding, starters, tài liệu/version đã chọn, tool business settings và capability toggles.

**Runtime Profile** thuộc Developer: provider/model, model parameters, embedding profile, provider-supported features, quotas cấp cao và core security policy.

Content Release chỉ lưu fingerprint của môi trường đã kiểm thử làm chứng cứ; Admin không sửa fingerprint và public/Admin API không trả raw runtime settings. Rollback nội dung không đổi model. Developer đổi model qua deployment/config workflow riêng.

### 13.2. Optimistic concurrency

Draft có revision/ETag; PATCH yêu cầu `If-Match`. Hai tab sửa đồng thời phải trả 409/412 có hướng dẫn cập nhật, không ghi đè lặng lẽ.

Evaluation gắn `draft_hash + selected_document_versions + tool_versions + runtime_fingerprint + security_epoch`. Sửa một phần liên quan làm evaluation cũ hết hiệu lực.

### 13.3. Publish transaction

1. Kiểm tra Admin đúng tenant và xác thực đủ mạnh.
2. Draft revision đúng; tất cả tài liệu được chọn ready, đúng public approval, không bị thu hồi.
3. Tool/capability vẫn được cấp và runtime đang hỗ trợ.
4. Evaluation required suite đã pass đúng hash, không dùng kết quả model cũ một cách ngầm định.
5. Tạo immutable release và release memberships.
6. Chuyển `active_release_id` trong cùng transaction có khóa chống publish cạnh tranh.
7. Ghi audit và outbox invalidation.
8. Chỉ sau commit mới báo publish thành công.

Thất bại giữa chừng giữ nguyên release cũ. Không chuyển active pointer sang index/tài liệu đang xử lý dở.

### 13.4. Phiên chat dùng release nào?

Production: mỗi lượt mới lấy active release ở thời điểm bắt đầu lượt; ghi release vào `chat_turns`. Trong một lượt giữ snapshot nhất quán, nhưng kiểm tra lại revocations/current permissions trước trả kết quả hoặc thực hiện Action.

`chat_sessions.pinned_release_id` chỉ dùng cho Preview/đánh giá có chủ đích; không cho công dân ép session production dùng release đã lỗi thời.

### 13.5. Rollback và emergency pause

Rollback chọn release nội dung cũ, kiểm tra còn tương thích Runtime Profile hiện tại và không chứa dữ liệu/tool đã bị thu hồi. Nếu không đạt thì chặn và chỉ rõ lý do; không dùng rollback làm lối tắt bỏ security policy.

Emergency pause có thể do Developer hoặc Admin trong phạm vi mình: ngừng chat mới/Action nguy hiểm, hiển thị đầu mối hỗ trợ cấu hình sẵn. Thông báo không chứa raw exception.

---

<a id="section-14"></a>

## 14. AI Orchestrator và OpenAI Adapter

### 14.1. Quyết định tích hợp

Dùng SDK OpenAI chính thức với Responses API ở backend; không scrape ChatGPT và không dùng Custom GPT ID làm API chatbot. Responses API hỗ trợ input/output và tool interactions; adapter phải xử lý các output item, không giả định mọi phản hồi chỉ có một text string [R02].

Không hardcode tên model từ hội thoại cũ. Developer điền model ID hợp lệ có quyền truy cập vào env/config. Khi chưa có key/model, local có Mock minh bạch; production không được tự chuyển Mock.

Không gán mặc định các tham số như `temperature` hoặc `reasoning_effort` cho mọi model. Compatibility manifest do Developer kiểm tra theo model được chọn; gửi tham số được hỗ trợ.

### 14.2. Interfaces

```python
# Hợp đồng thiết kế; Codex tạo dataclasses/Pydantic và implementation thực.
class ModelAdapter(Protocol):
    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
    async def stream(self, request: GenerationRequest) -> AsyncIterator[ProviderEvent]: ...
    async def healthcheck(self) -> ProviderHealth: ...

class EmbeddingAdapter(Protocol):
    async def embed(self, texts: list[str], profile: EmbeddingProfile) -> EmbeddingBatch: ...

class RetrievalService(Protocol):
    async def search(self, request: RetrievalRequest) -> EvidenceBundle: ...

class ActionGateway(Protocol):
    async def prepare(self, request: ActionRequest, context: TrustedContext) -> ActionProposal: ...
    async def confirm(self, proposal_id: UUID, confirmation: Confirmation, context: TrustedContext) -> Execution: ...
```

`GenerationRequest` do server dựng; frontend không gửi nguyên provider request. `GenerationResult` chứa answer/tool requests/usage/refusal/error chuẩn hóa. Provider metadata chỉ tồn tại kênh kỹ thuật đã redaction.

### 14.3. Luồng một lượt hỏi

```text
Authenticate/session ownership
  -> trusted TenantContext
  -> select active content release + technical runtime
  -> apply current policy + reserve budget
  -> classify intent (classification không cấp quyền)
  -> gather allowed evidence / expose minimum tools
  -> invoke model
  -> execute eligible read tools hoặc prepare write proposal
  -> validate answer / citations / current revocations
  -> persist terminal result + usage + audit references
  -> emit final events
```

Intent router có thể dùng rule và model; bất kỳ tool call nào vẫn phải qua Policy Engine. Model không quyết định người dùng có quyền hay không.

Đặt giới hạn khởi điểm: tối đa 4 vòng tool, 6 tool calls/turn, timeout tổng và output budget do Developer cấu hình. Khi vượt giới hạn, dừng có trạng thái, không vòng lặp agent vô hạn.

### 14.4. Tool calling đúng contract

Khai báo function tools với JSON Schema được SDK/model hỗ trợ. Nếu dùng strict mode, kiểm tra `additionalProperties=false`, các property required và field nullable đúng schema theo tài liệu [R03].

Parse arguments bằng JSON/schema; không dùng `eval`. Đối chiếu tool ID/version với registry đã cấp trước khi thực thi. Trả tool output theo đúng `call_id`; không chỉ xử lý item đầu tiên. Preserve các item cần thiết của vòng Responses theo SDK đã chọn.

Tool output được sanitize và giới hạn dung lượng; không đưa secret/token/raw HTTP headers vào prompt. External content vẫn là data, không trở thành instruction.

Write executor không được gọi trực tiếp chỉ vì model emit function call. Mô hình chỉ được chuẩn bị proposal; user confirmation endpoint mới thực thi.

### 14.5. Instructions nhiều lớp

- Lớp nền tảng bất biến: bảo mật, quyền, không bịa nguồn, bảo vệ dữ liệu.
- Lớp nghiệp vụ tenant: cách nói, phạm vi, hướng dẫn ưu tiên, do Admin viết.
- Runtime context: tenant, thời điểm, trạng thái xác thực đã rút gọn.
- Evidence/tool results/user attachments: dữ liệu không có quyền sửa các lớp trên.

Backend vẫn phải enforce, không coi prompt layering là tường bảo mật đủ dùng.

### 14.6. Stateful và lưu giữ

Ứng dụng quản lý lịch sử ở database của mình và chủ động gửi context cần thiết. Đề xuất `store=false` cho Responses phù hợp luồng này; không tuyên bố cờ đó đồng nghĩa không có mọi hình thức lưu giữ. Chính sách retention thay đổi theo endpoint/capability và thỏa thuận dữ liệu; phải kiểm tra tài liệu chính thức trước production [R05].

Không dùng response ID của người dùng khác làm conversation state. Không tái sử dụng hosted container/file/thread giữa tenant hoặc người dùng.

### 14.7. Retry, fallback và lỗi

Retry có backoff + jitter cho lỗi tạm thời/429 trong giới hạn; không retry vô hạn. Phân biệt authentication, invalid model, unsupported tool, timeout, quota và provider unavailable.

Fallback chỉ do Developer cấu hình, chỉ dùng khi đủ tương thích quyền/dữ liệu. Không tự chuyển provider ngoài chính sách để “cho có câu trả lời”.

Lời gọi có side effect không bị retry chỉ vì toàn bộ lượt model được retry. ActionGateway idempotency độc lập với model request.

Model thiếu nguồn trả thiếu nguồn; model/API lỗi trả tạm gián đoạn. Không dùng Mock answer hoặc kiến thức tưởng tượng để che lỗi production.


<a id="section-15"></a>

## 15. Capability Registry và tính năng mở rộng

### 15.1. Không chỉ tạo các checkbox

Mỗi capability có: ID, version, mô tả, trạng thái implementation, trạng thái cấu hình, principal được phép, data policy, quota, schema thiết lập nghiệp vụ, adapter và kiểm thử.

Hai trục trạng thái:

- Implementation: `not_implemented`, `implemented`, `verified`.
- Availability: `not_granted`, `not_configured`, `disabled`, `enabled`, `incompatible`, `temporarily_unavailable`.

`enabled` không đồng nghĩa đã được kiểm thử thành công với provider thật. Không hiển thị một công cụ có code rỗng thành “Sẵn sàng”.

### 15.2. Phạm vi phải xây

| ID | Capability | Cách triển khai/kiểm soát | Mặc định vận hành |
|---|---|---|---|
| CAP-01 | Knowledge Search | RetrievalService nội bộ, nguồn/version/ACL | Bật với kho đã publish |
| CAP-02 | Web Search | OpenAI web search adapter, domain allowlist, dẫn nguồn | Bật khi Developer cấp |
| CAP-03 | Actions | Application Tool Gateway, read/write policies | Theo từng connector |
| CAP-04 | Phân tích tài liệu người dùng | Attachment riêng phiên, scanner/parser, privacy gates | Yêu cầu đăng nhập cho dữ liệu cá nhân |
| CAP-05 | Code Interpreter | Sandbox hosted được hỗ trợ hoặc sandbox chuyên biệt đã kiểm định | Tắt, có thể cấp theo nhu cầu |
| CAP-06 | Image Generation | Adapter tạo ảnh thật, artifact storage và quota | Tắt, chỉ bật khi có mục đích |
| CAP-07 | Voice Input | Ghi âm có đồng ý, STT, sửa transcript trước gửi | Tùy cấu hình |
| CAP-08 | Voice Output | Đọc câu trả lời đã kiểm tra, TTS, nút dừng | Tùy cấu hình |
| CAP-09 | Custom Extensions/MCP | Connector được Developer đăng ký, qua Policy Engine | Chỉ danh mục được duyệt |

Tất cả các dòng thuộc phạm vi sản phẩm hoàn chỉnh. Thứ tự phát triển không đồng nghĩa bỏ hẳn các capability nâng cao. Khi thiếu key/quyền/model tương thích, code adapter và contract tests vẫn phải có, live verification ghi `blocked/not_run`, UI giải thích rõ.

### 15.3. Web Search

Sử dụng công cụ hỗ trợ domain filtering theo tài liệu OpenAI, đồng thời kiểm tra sources/annotations thực trả về và policy của ứng dụng [R07].

Danh sách domain do Developer phê duyệt; Admin có thể chọn tập con/nguồn đã được cấp. Không coi mọi website có đuôi `.gov.vn` là tự động phù hợp mọi câu hỏi.

Không gửi CCCD, mã hồ sơ riêng, access token hoặc hồ sơ nhạy cảm vào query web. Yêu cầu cá nhân dùng Action đã xác thực. Kết quả web không tự đưa vào Knowledge chính thức.

Khi model/tool không hỗ trợ allowlist theo cấu hình mong muốn thì khóa capability hoặc dùng adapter có giới hạn tương đương, không quietly bỏ filter.

### 15.4. User attachments khác Knowledge

Tài liệu công dân gửi chỉ thuộc phiên/người đó, TTL riêng, không xuất hiện trong kho Admin hoặc tìm kiếm của người khác. Khi muốn đưa tài liệu thành tri thức chung phải có quy trình upload/Admin phê duyệt riêng, không có “auto learn”.

Parse/scan và ACL áp dụng trước khi gửi AI. Không chia sẻ provider file ID/container giữa principal. Artifact đầu ra cũng có tenant/session ownership, kiểm tra MIME và TTL; không trả provider URL/token nguyên bản cho frontend.

Xử lý file dài theo giới hạn công khai; thông báo đã phân tích những phần nào, không tuyên bố đọc đầy đủ khi pipeline đã bỏ bớt.

### 15.5. Code Interpreter

OpenAI có Code Interpreter chạy trong môi trường sandbox; cấu hình và khả năng phụ thuộc công cụ/model [R08]. Không thay thế nó bằng `exec()` trên API/worker host.

Không mount secrets, database credentials hoặc Docker socket vào sandbox. Không tự mở network access nếu chưa được phê duyệt. File input/output được cấp theo phiên; có giới hạn thời gian, dung lượng và số lần chạy.

Mọi thao tác nghiệp vụ vẫn đi ActionGateway. Kết quả tính toán không tự được ghi vào hệ thống dịch vụ công. File tạo ra cần thông báo là kết quả hỗ trợ, không phải văn bản hành chính đã ký.

### 15.6. Image Generation

Tích hợp endpoint/tool chính thức được cấu hình, không giả ảnh bằng placeholder rồi báo thành công [R09]. Chỉ gọi theo yêu cầu có chủ đích, có quota và quản lý artifact.

Không phát sinh ảnh để “minh họa” hồ sơ, con dấu, chứng thực hoặc quyết định chính thức khiến người dùng hiểu nhầm. Đánh dấu nội dung do AI tạo; không tự nhận logo/chân dung tạo bằng AI là tư liệu chính thức của phường.

### 15.7. Voice

V1 dùng push-to-talk, không bắt buộc realtime voice liên tục. Hiển thị transcript cho người dùng sửa trước khi gửi; đặc biệt kiểm tra tên riêng, số hồ sơ, số tiền.

TTS chỉ đọc nội dung đã qua validator; không đọc token hoặc thông tin nhạy cảm tự động ngoài ý muốn. Có thông báo giọng đọc do AI tạo, chọn giọng trong danh mục cho phép, nút pause/stop. Các API audio/STT/TTS có hướng dẫn riêng, không dùng chat model name tùy ý thay cho model audio [R14][R15].

### 15.8. Custom extensions và MCP

Bản đầu ưu tiên application-side connectors qua ActionGateway. Thiết kế adapter MCP khi được cấp, nhưng lời gọi vẫn phải đi qua quyền, data policy và xác nhận của ứng dụng.

OpenAI hỗ trợ kết nối MCP; dữ liệu đi tới server bên thứ ba có ranh giới tin cậy riêng [R16]. Không bật tự khám phá rồi thực thi mọi tool của một server do Admin nhập.

Developer đăng ký endpoint, transport, version, danh sách tools, input/output schema, auth secret reference, risk level và egress rules. Admin chỉ bật/cấu hình phần nghiệp vụ đã cho phép.

Không load Python/JS/npm package tùy ý từ file upload. Không cho Admin upload ZIP “extension” rồi chạy trên server.

---

<a id="section-16"></a>

## 16. Actions, xác nhận và tính nhất quán giao dịch

### 16.1. Tool catalog

Mỗi tool có definition bất biến theo version, do Developer kiểm soát:

```json
{
  "tool_id": "lookup_my_application_status",
  "version": 1,
  "display_name": "Tra cứu hồ sơ của tôi",
  "risk_level": "personal_read",
  "requires_login": true,
  "connector_id": "public_service",
  "connector_version": 1,
  "required_scope": "application:read:self",
  "requires_confirmation": false,
  "input_schema": {
    "type": "object",
    "properties": {
      "application_code": {"type": "string", "minLength": 1, "maxLength": 80}
    },
    "required": ["application_code"],
    "additionalProperties": false
  },
  "allowed_business_config_keys": [],
  "timeout_seconds": 10,
  "retry_policy": "safe_read_only"
}
```

Đây là schema nội bộ, không phải thông số API dịch vụ công đã được cấp. `application:read:self` là permission nội bộ của ứng dụng. Chỉ serialize JSON Schema subset được provider hỗ trợ khi định nghĩa function tool.

Tool arguments không nhận `tenant_id`, `subject`, bearer token, endpoint URL, header auth hoặc secret. Backend inject các phần đó từ trusted context và connector configuration.

### 16.2. Danh mục gốc

| Tool | Tác động | Phụ thuộc |
|---|---|---|
| `get_public_contact` | Đọc giờ làm việc/địa chỉ/đầu mối đã cấu hình | Dữ liệu Admin phê duyệt |
| `search_public_procedures` | Đọc dữ liệu thủ tục công khai | Knowledge/API chính thức nếu có |
| `lookup_my_application_status` | Đọc thông tin cá nhân | IdP + API hồ sơ thật được cấp |
| `prepare_citizen_feedback` | Tạo proposal, chưa gửi đi | Nội dung từ người dùng |
| `submit_citizen_feedback` | Gửi phản ánh thật | Chỉ executor sau xác nhận, connector thật |
| `prepare_appointment` | Tạo proposal đặt lịch | Connector lịch có thật |
| `create_appointment` | Đặt lịch thật | Sau xác nhận, chống đặt trùng |

Không bắt buộc đặt lịch live nếu chưa có API; phải ghi external dependency và không gọi đó là nghiệp vụ đã tích hợp. Framework, stub kiểm thử và disabled state phải có.

### 16.3. Phân tầng rủi ro

`public_read`, `personal_read`, `write_reversible`, `write_sensitive`. Nghiệp vụ có hiệu lực pháp lý vượt phạm vi cho phép phải bị khóa, không tự suy ra quyền từ câu chữ người dùng.

Một Action HTTP GET không mặc nhiên an toàn nếu endpoint có side effect; phân loại theo nghiệp vụ, không chỉ HTTP method.

### 16.4. Proposal và confirmation

Proposal phải lưu:

- Tenant, principal đã xác thực, session, tool/version và release.
- Payload canonical, payload hash, summary hiển thị cho công dân.
- Nonce một lần, expiry (mặc định đề xuất 5 phút).
- Trạng thái, người xác nhận, thời điểm và policy fingerprint.

UI hiển thị chính xác đối tượng nhận, nội dung, dữ liệu cá nhân và hậu quả. Người dùng sửa nội dung → proposal cũ hết hiệu lực → tạo proposal mới → xác nhận lại.

Câu “đồng ý” trong một đoạn web, file hoặc tool output không được xem là xác nhận. Một tool call của model cũng không phải xác nhận. Bản đầu dùng nút xác nhận rõ ràng qua endpoint có CSRF/auth, không cho model tự gọi endpoint này.

### 16.5. State machine

```text
draft -> awaiting_confirmation
awaiting_confirmation -> confirmed | cancelled | expired
confirmed -> executing
executing -> succeeded | failed | unknown
unknown -> succeeded | failed | manual_review
```

Không có transition `unknown -> executing` tự động nếu chưa chứng minh upstream chưa thực hiện.

### 16.6. Idempotency và timeout

Trong transaction: kiểm tra proposal/payload hash/expiry/actor/current policy → consume nonce → tạo execution unique → ghi outbox. Worker nhận execution ID, re-check quyền liên quan, gửi cùng idempotency key cho upstream khi upstream hỗ trợ.

Nếu upstream đã xử lý nhưng trả lời bị mất, trạng thái là `unknown`; dùng status endpoint/reference để đối soát. Không gửi lại với key mới để thử vận may.

Không thể hứa “exactly once” xuyên hai hệ thống khi upstream không hỗ trợ. Khi không có idempotency hoặc reconciliation, tắt retry thao tác ghi và yêu cầu kiểm tra thủ công.

Hành động đã thành công phải lấy thông tin từ execution record, không dựa vào model viết “đã gửi”. Return reference/timestamp thật; chưa có reference thì không tạo mã giả.

### 16.7. Secrets và giới hạn connector

Secrets lưu trong secret manager hoặc secret file server-side, registry chỉ lưu `secret_ref`. Admin chỉ thấy “Đã cấu hình/Chưa cấu hình”, không xem và không nhập API key AI.

Endpoint/base URL/auth schema của Action do Developer sở hữu. Không cho Admin đặt endpoint localhost/private tùy ý. Tham số nghiệp vụ được phép như mã bộ phận nhận phản ánh phải được schema validation và giới hạn danh mục.

Connector response có output schema, allowlist field, size cap, timeout, error mapping. Raw upstream response có dữ liệu nhạy cảm không đưa thẳng vào model/log/UI.

### 16.8. Preview và thử Action

Read public có thể test thật trong quota. Personal read dùng tài khoản sandbox/chính người đang được ủy quyền, không nhập subject tùy ý. Write luôn dry-run ở Playground và evaluation.

Production connector chưa cấu hình → `ACTION_NOT_CONFIGURED`; không fallback sang fake success.

---

<a id="section-17"></a>

## 17. Hợp đồng API ứng dụng

### 17.1. Quy ước

Prefix `/api/v1`; JSON UTF-8; cursor pagination; UUID; UTC timestamps. Response envelope và error code thống nhất. FastAPI sinh OpenAPI; frontend client/types được generate để tránh lệch schema.

Schema request `extra="forbid"` cho DTO quản trị và các điểm nhạy cảm. Auth/tenant không lấy từ input khi đã có context server.

### 17.2. Nhóm endpoint

| Method | Endpoint | Quyền / chức năng |
|---|---|---|
| GET | `/public/assistants/{public_key}` | Cấu hình widget công khai đã lọc |
| POST | `/public/assistants/{public_key}/sessions` | Tạo anonymous session, rate limit |
| POST | `/citizen/assistants/{public_key}/sessions` | Tạo session đã xác thực |
| POST | `/chat/sessions/{session_id}/turns` | Tạo lượt hỏi, idempotency |
| GET | `/chat/turns/{turn_id}` | Trạng thái/result, kiểm tra ownership |
| GET | `/chat/turns/{turn_id}/events` | SSE, auth theo session |
| POST | `/chat/turns/{turn_id}/cancel` | Hủy best-effort, không đảo ngược Action đã gửi |
| POST | `/chat/turns/{turn_id}/feedback` | Đánh giá đúng phiên |
| POST | `/chat/sessions/{session_id}/attachments` | Upload riêng phiên nếu được phép |
| DELETE | `/chat/sessions/{session_id}` | Xóa/đóng theo retention policy |
| GET | `/sources/{citation_id}` | Nguồn dẫn có kiểm tra ACL/public release |
| POST | `/auth/admin/login` | Admin password login |
| POST | `/auth/admin/mfa/verify` | Xác thực MFA |
| POST | `/auth/logout` | Thu hồi phiên |
| GET | `/auth/me` | Principal đã lọc, không raw token |
| GET | `/auth/citizen/start` | Bắt đầu OIDC |
| GET | `/auth/citizen/callback` | Xác minh OIDC |
| GET | `/admin/dashboard` | Dashboard tenant |
| GET | `/admin/assistant` | Cấu hình nghiệp vụ, không runtime model |
| PATCH | `/admin/assistant/draft` | Lưu nháp với If-Match |
| POST | `/admin/assistant/preview/sessions` | Preview draft đúng tenant |
| GET/POST | `/admin/knowledge/documents` | List/tạo metadata |
| POST | `/admin/knowledge/uploads` | Upload batch, job IDs từng file |
| GET | `/admin/knowledge/jobs/{id}` | Tiến độ, cảnh báo, lỗi |
| GET/PATCH | `/admin/knowledge/documents/{id}` | Chi tiết/metadata, optimistic locking |
| POST | `/admin/knowledge/documents/{id}/versions` | Upload phiên bản mới |
| POST | `/admin/knowledge/texts` | Văn bản/FAQ mới |
| POST | `/admin/knowledge/versions/{id}/approve-public` | Xác nhận công khai có audit |
| POST | `/admin/knowledge/documents/{id}/revoke` | Thu hồi ngay |
| POST | `/admin/knowledge/documents/{id}/delete-request` | Workflow purge theo policy |
| GET/POST | `/admin/website-sources` | Nguồn trong domain được cấp |
| PATCH | `/admin/website-sources/{id}` | Rules/lịch trong giới hạn |
| POST | `/admin/website-sources/{id}/sync` | Job sync |
| GET | `/admin/website-sources/{id}/runs` | Trạng thái/diff |
| GET/PATCH | `/admin/capabilities` | Đọc/cấu hình trong quyền được cấp |
| GET | `/admin/actions` | Danh mục được cấp, fields nghiệp vụ |
| PATCH | `/admin/actions/{binding_id}` | Chỉ business config allowlist |
| POST | `/admin/actions/{binding_id}/test` | Sandbox/dry-run, không bypass |
| GET/POST | `/admin/evaluation-cases` | Bộ câu hỏi |
| POST | `/admin/evaluations` | Tạo test run |
| GET | `/admin/evaluations/{id}` | Kết quả |
| POST | `/admin/releases/validate` | Preflight publish |
| POST | `/admin/releases` | Publish đúng hash/revision |
| GET | `/admin/releases` | Lịch sử |
| POST | `/admin/releases/{id}/rollback` | Kiểm tra và rollback nội dung |
| POST | `/admin/assistant/pause` | Dừng chatbot tenant |
| GET | `/admin/conversations` | Lịch sử theo policy/redaction |
| GET | `/admin/usage` | Thống kê không model/provider |
| GET | `/admin/audit` | Nhật ký phạm vi tenant |
| POST | `/actions/proposals/{id}/confirm` | Citizen auth + nonce + hash |
| POST | `/actions/proposals/{id}/cancel` | Chủ proposal |
| GET | `/actions/executions/{id}` | Trạng thái đúng chủ thể |
| POST | `/audio/transcriptions` | Attachment và quyền hợp lệ |
| POST | `/audio/speech` | Nội dung đã kiểm tra, quota |
| GET | `/artifacts/{id}/download` | ACL, TTL, URL ngắn hạn hoặc proxy |

Không tạo public `/admin/models`, `/providers`, `/set-model`, `/run-python`, `/call-url` hoặc `/execute-any-tool`. Công cụ vận hành kỹ thuật là CLI/private control plane.

### 17.3. Ví dụ DTO Admin

```json
{
  "revision": 4,
  "name": "Trợ lý thông tin phường",
  "description": "Hỗ trợ tra cứu thông tin và hướng dẫn",
  "instructions": "Trả lời lịch sự, ưu tiên nguồn của phường đã được phê duyệt.",
  "welcome_message": "Xin chào, bạn cần hỗ trợ nội dung gì?",
  "conversation_starters": ["Tôi muốn tìm hướng dẫn thủ tục"],
  "knowledge_version_ids": [],
  "capabilities": {
    "knowledge_search": true,
    "web_search": false,
    "actions": true,
    "document_analysis": false,
    "code_interpreter": false,
    "image_generation": false,
    "voice_input": false,
    "voice_output": false,
    "custom_extensions": false
  },
  "action_binding_ids": [],
  "branding": {
    "primary_color": "#145B86",
    "logo_asset_id": null
  }
}
```

Màu trên là gợi ý giao diện, không phải yêu cầu thương hiệu chính thức. Backend kiểm tra toàn bộ version IDs/action bindings thuộc tenant. `revision`/ETag không phải giấy phép thay quyền.

### 17.4. Ví dụ gửi tin

```json
{
  "client_request_id": "uuid-do-client-tao",
  "message": "Tôi muốn biết cần chuẩn bị gì cho thủ tục này.",
  "attachment_ids": []
}
```

Backend trả `202 Accepted`:

```json
{
  "turn_id": "uuid",
  "state": "queued",
  "events_path": "/api/v1/chat/turns/uuid/events",
  "request_id": "uuid"
}
```

Không trả hoặc nhận model/provider. Attachment IDs không thuộc session trả 404/403 mà không lộ chủ file.

### 17.5. Error envelope

```json
{
  "error": {
    "code": "ACTION_CONFIRMATION_EXPIRED",
    "message": "Yêu cầu xác nhận đã hết hạn. Vui lòng kiểm tra lại nội dung trước khi gửi.",
    "request_id": "uuid",
    "retryable": false
  }
}
```

Các mã tối thiểu: `AUTH_REQUIRED`, `SESSION_EXPIRED`, `MFA_REQUIRED`, `FORBIDDEN`, `RESOURCE_NOT_FOUND`, `VALIDATION_ERROR`, `VERSION_CONFLICT`, `TENANT_PAUSED`, `RATE_LIMITED`, `BUDGET_EXCEEDED`, `FILE_UNSUPPORTED`, `FILE_TOO_LARGE`, `FILE_QUARANTINED`, `EXTRACTION_REVIEW_REQUIRED`, `KNOWLEDGE_NOT_READY`, `SOURCE_REVOKED`, `CAPABILITY_DISABLED`, `CAPABILITY_INCOMPATIBLE`, `ACTION_NOT_CONFIGURED`, `ACTION_CONFIRMATION_EXPIRED`, `ACTION_PAYLOAD_CHANGED`, `ACTION_OUTCOME_UNKNOWN`, `AI_UNAVAILABLE`.

Log kỹ thuật có detail đã redaction; client chỉ nhận thông tin an toàn. Không trả stack trace, provider account ID hoặc tên model qua lỗi.

---

<a id="section-18"></a>

## 18. Streaming, concurrency và UX khi xảy ra lỗi

### 18.1. Hai bước tạo lượt và đọc SSE

POST tạo turn idempotent trong DB + outbox; worker/API executor xử lý; GET events trả stream theo ownership. Frontend dùng `fetch` streaming khi cần Authorization header cho anonymous token; không đặt secret trong query để dùng EventSource.

Auth bằng first-party cookie ở trang chat đã login và CSRF cho request ghi. Kiểm tra quyền khi reconnect, không chỉ lần tạo stream.

### 18.2. Event contract

```text
turn.created
turn.status              # searching / preparing / generating / validating
turn.evidence_ready      # chỉ nguồn được phép hiển thị
answer.delta             # chỉ nội dung đã qua chính sách theo chế độ bên dưới
action.confirmation_required
artifact.ready
turn.completed
turn.failed
turn.cancelled
```

Mỗi event có `event_id`, `turn_id`, `sequence`, timestamp và payload có schema. Heartbeat định kỳ; replay với Last-Event-ID trong retention window; terminal result luôn lấy lại được từ DB nếu buffer Redis hết.

Không stream chain-of-thought hoặc raw tool arguments nhạy cảm. Dòng “đang tìm nguồn” là status thật, không bịa AI đang kiểm chứng khi pipeline chưa làm.

### 18.3. Không để streaming phá vỡ kiểm tra câu trả lời

Đối với thủ tục, pháp lý, dữ liệu cá nhân và Actions: buffer kết quả có cấu trúc, kiểm tra nguồn/quyền rồi mới phát nội dung answer. UI vẫn nhận status theo thời gian thực. Có thể chia nội dung đã duyệt thành các đoạn để hiển thị, nhưng không gọi đó là raw token stream từ model.

Nếu muốn token streaming trực tiếp cho chào hỏi ít rủi ro, tách chế độ rõ; không áp dụng cho nội dung cần pre-validation.

### 18.4. Concurrency

Một session tối đa một turn đang generate ở baseline. Request trùng `client_request_id` trả lại turn cũ; message mới khi đang xử lý trả trạng thái conflict hoặc queue có thứ tự, chọn một cách và test.

Worker dùng lease/state transition chống chạy đôi; lease hết và crash recovery không được thực thi lại write action vô điều kiện.

Cancel là best-effort: ngắt provider request khi được hỗ trợ, đánh dấu không tiếp tục tool mới; chi phí có thể đã phát sinh. Action đã xác nhận/gửi upstream không được UI báo “đã hủy” chỉ vì người dùng đóng chat.

### 18.5. Khi AI hoặc dịch vụ ngoài lỗi

Hiển thị thông báo đơn giản, trạng thái connector và đầu mối hỗ trợ đã cấu hình. Không trả câu trả lời giả cho mục đích che lỗi. Retry UI dùng request ID/idempotency tương thích, không tạo phản ánh mới.


<a id="section-19"></a>

## 19. Bảo mật, riêng tư và các cổng chặn production

### 19.1. Bảo mật ứng dụng

TLS production; request IDs; CSP; chống XSS trong Markdown/HTML; CSRF cho cookie-based writes; CORS đúng origin; giới hạn upload/request body; HTTP client có timeout; log redaction; dependency/security scanning.

Chỉ mount volume cần thiết; container non-root khi khả thi; không mount Docker socket; hạn chế outbound network theo loại worker. Parser/OCR có sandbox/process/resource limits để file hỏng không đánh sập API.

Prompt injection cần defense-in-depth: giới hạn tools, phân quyền thật, evidence không phải instructions, output validation và confirmation. Không coi một classifier “phát hiện prompt độc” là cơ chế bảo vệ duy nhất.

Không ghi lại hidden chain-of-thought. Audit chỉ cần quyết định nghiệp vụ, evidence IDs, tool call đã làm sạch, actor, timestamp và kết quả.

### 19.2. Data policy

Các lớp: `public`, `internal`, `personal`, `restricted`. Kho chatbot công dân chỉ dùng dữ liệu `public` đã được phê duyệt. Tài liệu nội bộ không tự xuất hiện trong chat công khai. Dữ liệu `restricted` chặn gửi ra AI bên ngoài trừ khi có quy trình và phê duyệt phù hợp; bản đầu nên chặn hoàn toàn loại này trong public chatbot.

Chọn cloud trong nước không tự làm cho các request tới OpenAI trở thành xử lý nội địa. Cần lập data-flow inventory: dữ liệu nào, xử lý ở đâu, mục đích, provider retention, người được đọc và cách xóa. Tài liệu OpenAI mô tả data controls theo endpoint; việc bật các hosted tools cần xét riêng [R05].

Không tự tuyên bố “đáp ứng toàn bộ pháp luật” hoặc “được phép xử lý hồ sơ thật” chỉ vì phần mềm có TLS/RLS. Đơn vị quản lý phải phê duyệt hạ tầng, phân loại dữ liệu, yêu cầu an toàn thông tin, hợp đồng xử lý dữ liệu và phương án tích hợp.

### 19.3. Mặc định retention đề xuất, không phải thời hạn luật định

| Loại | Local/test | Production baseline cần phê duyệt |
|---|---|---|
| Anonymous raw chat | Ngắn hạn phục vụ debug | Đề xuất 30 ngày hoặc ngắn hơn theo mục đích |
| Session attachments | 24 giờ | Đề xuất 24 giờ sau xử lý, có giới hạn phiên |
| Personal chat | Chỉ dữ liệu giả | Tắt lưu raw mặc định; lưu tối thiểu theo policy được duyệt |
| Evaluation fixtures | Dữ liệu giả | Không đưa PII thật vào regression suite |
| Usage aggregates | Lưu số liệu test | Tổng hợp không PII, theo nhu cầu kế toán/quota |
| Security/audit events | Test log | Thời hạn do đơn vị phê duyệt; redaction bắt buộc |
| Backups | Dữ liệu local | Thời hạn, mã hóa và quy trình xóa được phê duyệt |

Purge có lịch, idempotency và test. Backup có thể chứa dữ liệu đã xóa khỏi live DB; cần lịch hết hạn backup, deletion ledger và quy trình áp dụng lại xóa khi restore. Không hứa xóa tức thì khỏi mọi backup nếu chưa có cơ chế tương ứng.

### 19.4. Go-live gates

Trước khi gọi production ready phải có:
- Review phân quyền, tenant isolation, secrets, upload, SSRF, prompt injection và Actions.
- Thẩm định data flow/retention/hạ tầng của đơn vị.
- Key, model và capability compatibility đã được Developer kiểm thử thật.
- Domain/TLS, IdP và connector được xác nhận, không placeholder.
- Live connector ghi được thử trong sandbox, có reconciliation/idempotency.
- Restore test từ backup; monitoring/alert người nhận rõ.
- Không có demo credentials, fake citizen login hoặc mock provider trong production.
- Bộ đánh giá nội dung được cán bộ nghiệp vụ xác nhận.
- Quy trình xử lý incident, thu hồi tài liệu, dừng Actions và thay Admin.

Chưa đủ gate thì báo đúng phần còn thiếu, không tháo gate để “đưa lên cho nhanh”.

---

<a id="section-20"></a>

## 20. Cấu hình kỹ thuật chỉ dành cho Developer

### 20.1. Runtime config

Đọc từ env/secret manager và file cấu hình kỹ thuật có version. Không lưu vào `assistant_drafts.config_json` của Admin.

```yaml
# technical-runtime.example.yaml
runtime_version: "dev-config-v1"
ai:
  provider: "openai"
  chat_model: "${OPENAI_CHAT_MODEL}"
  fallback_model: null
  store_responses: false
  timeout_seconds: 60
  max_tool_rounds: 4
  max_tool_calls_per_turn: 6
embedding:
  provider: "${EMBEDDING_PROVIDER}"
  model: "${OPENAI_EMBEDDING_MODEL}"
  dimensions: "${EMBEDDING_DIMENSIONS}"
  profile_id: "${EMBEDDING_PROFILE_ID}"
policy:
  allow_mock_in_production: false
  personal_data_external_processing_approved: false
  enforce_write_confirmation: true
  require_public_source_approval: true
```

Đây là file cấu hình nội bộ; không gửi nguyên khối cho OpenAI. Mỗi tham số được validate khi startup. `personal_data_external_processing_approved` là policy do Developer thiết lập sau phê duyệt thực tế, không phải một checkbox Admin có thể bật thay cho thủ tục phê duyệt.

### 20.2. `.env.example`

```dotenv
APP_ENV=local
APP_NAME=ai-citizen-platform
APP_PUBLIC_URL=http://localhost:8080
APP_LOCAL_PORT=8080
DISPLAY_TIMEZONE=Asia/Ho_Chi_Minh

# Bootstrap sinh secrets/connection strings local. Production dùng secret manager.
DATABASE_URL=
MIGRATION_DATABASE_URL=
REDIS_URL=redis://redis:6379/0
SESSION_SECRET=
ENCRYPTION_KEY=
TRUSTED_PROXY_CIDRS=
COOKIE_SECURE=false

# Mock chỉ local/test. Đổi sang openai bằng cấu hình Developer.
AI_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=
OPENAI_FALLBACK_CHAT_MODEL=
OPENAI_STORE_RESPONSES=false
AI_REQUEST_TIMEOUT_SECONDS=60

EMBEDDING_PROVIDER=mock
OPENAI_EMBEDDING_MODEL=
EMBEDDING_DIMENSIONS=
EMBEDDING_PROFILE_ID=

# Technical capabilities; model IDs không xuất hiện ở Admin.
OPENAI_TRANSCRIPTION_MODEL=
OPENAI_TTS_MODEL=
OPENAI_IMAGE_MODEL=
ENABLE_HOSTED_CODE_INTERPRETER=false
ENABLE_REMOTE_MCP=false

S3_ENDPOINT=http://minio:9000
S3_REGION=local
S3_BUCKET=ai-citizen-private
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=

MAX_UPLOAD_MB=25
MAX_PDF_PAGES=300
MAX_UPLOAD_FILES_PER_BATCH=10
ANTIVIRUS_REQUIRED=false

OIDC_ENABLED=false
OIDC_ISSUER=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
OIDC_REDIRECT_URI=
ALLOW_LOCAL_TEST_IDENTITY=true

PERSONAL_DATA_EXTERNAL_PROCESSING_APPROVED=false
PRICING_CATALOG_PATH=
RUN_LIVE_API_TESTS=false
```

Khóa encryption/session/storage là secrets thật, không để `changeme`. Chỉ biến URL công khai cần thiết được phép có prefix `NEXT_PUBLIC_`. Không dùng prefix đó cho provider, model ID, token hoặc database.

### 20.3. Readiness và fail closed

Production startup/readiness chặn nếu:
- `AI_PROVIDER=mock`, `ALLOW_LOCAL_TEST_IDENTITY=true`, cookie insecure, default secrets.
- Thiếu model/key cho các capability đang cấp mà không có trạng thái disabled rõ.
- RLS/migration chưa sẵn sàng, storage private sai, scanner bắt buộc không hoạt động.
- Cấu hình embedding dimension sai hoặc khác index profile.
- Thiếu chính sách privacy đã chấp thuận cho luồng personal data được bật.

Không probe provider bằng lời gọi tính phí liên tục ở healthcheck. Tách liveness process, readiness infrastructure và trạng thái provider last-check có cache. Lỗi nhà cung cấp không được gây restart storm cho mọi pod/process.

### 20.4. Model rollout

Developer: sửa runtime config → validate adapter compatibility → chạy regression/sandbox tools → canary nội bộ → triển khai → theo dõi → rollback kỹ thuật nếu cần.

Content release từng phường giữ nguyên nhưng evidence/evaluation có thể cần chạy lại. Runtime fingerprint được ghi ở log kỹ thuật và từng turn để điều tra; Admin chỉ thấy thông báo chung khi một capability tạm không tương thích.

Đổi embedding profile phải build song song index, không đổi biến env rồi dùng vector cũ.

---

<a id="section-21"></a>

## 21. Triển khai, lệnh chạy và vận hành

### 21.1. Compose local

Services cần có: `web`, `api`, `worker`, `scheduler`, `postgres`, `redis`, `minio`, `nginx`; antivirus và IdP local có thể là profile riêng. Worker OCR có thể tách queue/process.

Persistent volumes cho DB/storage; healthchecks; migration one-shot job; seed local idempotent. Không chạy migration đua nhau ở mọi API replica. Không tự tạo schema bằng `create_all()` thay migration.

Service nội bộ không public internet. Local bind gateway `127.0.0.1:${APP_LOCAL_PORT}`; chỉ công bố DB/storage console ở localhost khi có profile debug rõ.

### 21.2. Scripts Codex phải thực sự tạo

Các lệnh dưới đây là **hợp đồng cần được triển khai và kiểm thử trong repository**, không phải thông báo chúng đã tồn tại khi mới đọc đặc tả.

Windows PowerShell:

```powershell
# Từ thư mục repository
.\scripts\bootstrap.ps1
.\scripts\dev.ps1
.\scripts\check.ps1
docker compose ps
docker compose logs --tail 100 api worker web
```

Linux:

```bash
bash scripts/bootstrap.sh
bash scripts/dev.sh
bash scripts/check.sh
docker compose ps
docker compose logs --tail 100 api worker web
```

Script phải:
- Xác định root tương đối từ vị trí script, hỗ trợ đường dẫn có dấu và khoảng trắng.
- Kiểm tra Docker CLI **và Docker Engine**, không chỉ `docker --version`.
- Nếu Windows Docker Desktop Linux Engine chưa chạy, báo hướng dẫn cụ thể và dừng sạch.
- Kiểm tra port bị chiếm; không tự kill process.
- Sinh `.env` local an toàn khi chưa có; không ghi đè `.env` đang dùng.
- Không thay ExecutionPolicy toàn máy, không yêu cầu quyền Admin không cần thiết.
- Không xóa volume hoặc tải/cài tool ngoài mà không minh bạch.
- Kết thúc hiển thị URL thật đang chạy, trạng thái health và cách lấy tài khoản local đã provision.
- Bảo đảm chạy lần hai không reset Knowledge/Admin đang có.

### 21.3. CLI kỹ thuật

Codex tạo CLI với các chức năng sau, tên có thể nhất quán theo package:

```bash
python -m citizen_ai.cli ops create-tenant --slug ward-demo-a --name "Phuong mau A"
python -m citizen_ai.cli ops provision-admin --tenant ward-demo-a --email admin-a@example.invalid
python -m citizen_ai.cli ops rotate-admin --tenant ward-demo-a --email new-admin@example.invalid
python -m citizen_ai.cli ops grant-capability --tenant ward-demo-a --capability knowledge_search
python -m citizen_ai.cli ops validate-runtime
python -m citizen_ai.cli ops seed-demo
python -m citizen_ai.cli ops run-evaluations --tenant ward-demo-a
python -m citizen_ai.cli ops backup-check
```

`seed-demo` phải từ chối production. Password được nhập an toàn hoặc sinh local-only; không truyền password/API key trên command line dễ rơi vào shell history. CLI đặc quyền chạy trong môi trường vận hành được phép, không expose thành route internet.

`provision-admin` có constraint một Admin active, `rotate-admin` thu hồi phiên cũ. CLI quản trị không có quyền đọc mọi hội thoại trừ khi quy trình break-glass riêng được phê duyệt và audit.

### 21.4. Production packaging

Có compose production override, image build nhiều stage, bỏ dev server/source mount, non-root, secrets riêng, resource limits, restart policy, logs và TLS. Docker có hướng dẫn riêng cho khác biệt cấu hình Compose development/production [R18].

Một máy chạy Compose là single-host deployment, không tự có high availability. Hai API instance nhưng chỉ một DB/gateway/storage vẫn có điểm lỗi đơn.

### 21.5. So sánh hạ tầng cần ghi trong DEPLOYMENT.md

| Phương án | Điều cần triển khai | Ranh giới cần làm rõ |
|---|---|---|
| Cloud/VPS trong nước | App, DB, storage, backup và giám sát | OpenAI vẫn là dịch vụ ngoài; cần data-flow approval |
| Cloud quốc tế | Managed services hoặc VM, network, backup | Region, hợp đồng, dữ liệu được phép lưu/xử lý |
| Hạ tầng đơn vị/on-premise | Server, điện/mạng, patch, backup, nhân sự vận hành | Không có GPU vẫn chạy API; model nội bộ là dự án adapter/hạ tầng riêng |

Không tự khóa vào một vendor, không dựng cloud resources trả phí chỉ để hoàn tất test. Hướng dẫn production phải nêu DNS, cert, firewall, outbound access, migration, rollback và backup restore.

### 21.6. Monitoring và sự cố

Metrics: request count/latency, active turns, queue depth/age, ingestion failures, OCR warnings, retrieval latency, no-evidence rate, model/API errors, tool calls, duplicate action suppression, outcome unknown, quota và purge status.

Logs JSON có correlation IDs; không dùng full citizen message/CCCD làm label metric. Dashboard vận hành kỹ thuật riêng với quyền hạn chế, không mở Grafana public.

Runbooks tối thiểu: provider 429/outage; database/storage full; worker backlog; tài liệu sai; rò tenant nghi ngờ; mất Admin; connector write timeout; ngân sách bất thường; restore và incident notification.

### 21.7. Backup và restore

Backup DB + file manifest + objects cần thiết + cấu hình version, mã hóa và lưu tách môi trường. Keys phục hồi có quy trình riêng.

Mục tiêu đề xuất để đánh giá: RPO không quá 1 giờ, RTO không quá 4 giờ nếu đơn vị chấp thuận và hạ tầng hỗ trợ. Daily backup đơn thuần không đáp ứng RPO này; cần incremental/WAL/PITR phù hợp. Đây là mục tiêu phải đo trong restore drill, không phải cam kết đã đạt.

Sau restore kiểm tra RLS, tenant membership, source/object links, security epoch, deletion ledger và không chạy lại Action write cũ.

---

<a id="section-22"></a>

## 22. Usage, quota và dự toán chi phí

### 22.1. Không hardcode bảng giá hoặc model chưa xác minh

Giá phụ thuộc model, input/output/cache, embeddings và hosted tools; lấy rate card chính thức khi Developer cấu hình và lưu ngày hiệu lực [R17]. Không tái dùng con số suy đoán từ trao đổi cũ.

`pricing_catalog` là dữ liệu Developer-managed, có currency, unit, model/tool key, effective_from và source. Giá thiếu phải hiện `unknown/unpriced`, không mặc định bằng 0.

### 22.2. Cost ledger

Mỗi request/turn/job ghi usage thực trả về và cost estimate:

```text
model_cost =
  uncached_input_units * uncached_input_rate
  + cached_input_units * cached_input_rate
  + billed_output_units * output_rate

total_cost =
  model_cost
  + embeddings_cost
  + hosted_tool_cost
  + storage_cost
  + audio/image/ocr_cost_if_applicable
```

Đối soát tránh đếm hai lần output/reasoning tokens theo cấu trúc usage và pricing của model thực dùng. Tách chi phí từng operation để không vừa tính trong tool vừa tính lại tổng.

Chi phí hạ tầng, backup, monitoring và nhân sự không trộn vào token bill. Báo cáo dự toán phải hiển thị assumptions và phần chưa đo.

### 22.3. Budget control

Đặt per-tenant daily/monthly budget và rate limits do Developer cấp. Trước lời gọi tính phí: reserve có transaction/atomic operation, giới hạn output/tool count; sau kết quả reconcile actual usage và giải phóng phần dư.

Nhiều request song song không được cùng đọc “còn ngân sách” rồi đều tiêu không giới hạn. Crash có cleanup reservation và reconciliation, không đơn giản hoàn tiền toàn bộ khi provider có thể đã tính phí.

Alert ở các mức cấu hình được; vượt ngưỡng dừng công cụ tùy chọn trước. Giới hạn phía ứng dụng không bảo đảm bill provider tuyệt đối không vượt khi telemetry trễ, cần provider quota/alert và đối soát.

### 22.4. Quy mô thiết kế để thử tải

Baseline thử nghiệm đề xuất: 10 tenant, 100.000 câu hỏi/tháng toàn hệ thống, 30 chat turn đồng thời, kho dữ liệu theo bộ fixture mở rộng. Đây là input benchmark, không phải dự báo lưu lượng người dùng đã xác nhận.

Tách kết quả:
- Platform-only với adapter giả lập latency có kiểm soát.
- End-to-end live API trên lượng request nhỏ được phép tính phí.
- Ingestion/OCR riêng.
- Workload có tenant filter/ACL thật.

Không dùng kết quả mock local để tuyên bố chất lượng hay độ trễ OpenAI thực tế.

---

<a id="section-23"></a>

## 23. Kiểm thử bắt buộc và tiêu chí nghiệm thu

### 23.1. Test layers

Unit tests; integration với PostgreSQL/Redis thật; provider adapter contract tests; tenant isolation tests; browser E2E; security tests; AI evaluation; load/soak tests; restore drill.

Không thay PostgreSQL bằng SQLite cho các test RLS, vector hoặc transaction/idempotency. Chạy app queries bằng runtime DB role, không test bằng superuser rồi kết luận RLS đúng.

Live API tests phải opt-in bằng flag và key, giới hạn chi phí; không chạy live mặc định mọi lần CI.

### 23.2. Danh sách kịch bản tối thiểu

| ID | Kịch bản | Kết quả bắt buộc |
|---|---|---|
| T-01 | Admin A mở document B bằng ID | Không đọc được, không lộ thông tin |
| T-02 | Admin A attach document_version B vào release A | Backend/FK từ chối |
| T-03 | RAG A với câu hỏi trùng nội dung B | Không lấy chunk B |
| T-04 | Worker thiếu TenantContext | Không truy cập tenant rows |
| T-05 | Reuse connection pool A rồi B | Không giữ tenant context A |
| T-06 | Citation/artifact/session IDs của người khác | Từ chối |
| T-07 | Cache cùng câu hỏi ở hai tenant | Không dùng chung answer/evidence |
| T-08 | SSE reconnect tới turn khác | Từ chối |
| T-09 | Runtime role đọc DB không context | Default-deny |
| T-10 | Admin PATCH chứa model/provider/API key | Validation/authorization từ chối |
| T-11 | Instructions yêu cầu đổi model | Runtime không đổi |
| T-12 | Admin export/dashboard/preview/errors | Không lộ model/provider/secrets |
| T-13 | Developer đổi chat model | Core Knowledge giữ nguyên, test được chạy lại |
| T-14 | Đổi embedding dimension | Chặn dùng index cũ, yêu cầu reindex |
| T-15 | Admin bật capability chưa cấp | Từ chối |
| T-16 | Capability không tương thích runtime | Khóa và báo rõ |
| T-17 | Upload PDF nhiều trang | Có coverage mọi trang hoặc lỗi rõ |
| T-18 | PDF scan tiếng Việt | OCR, locator, review warning đúng |
| T-19 | XLSX nhiều sheet/merged/formula/hidden | Không mất quan hệ; cảnh báo đúng |
| T-20 | File giả MIME, quá lớn, nén độc hại | Chặn/quarantine |
| T-21 | File chứa script/macro/prompt injection | Không thực thi/không nâng quyền |
| T-22 | Upload cùng file/retry worker | Không trùng dữ liệu sai |
| T-23 | Job worker crash và chạy lại | Trạng thái/chunk nhất quán |
| T-24 | Tài liệu draft chưa publish | Công dân không thấy |
| T-25 | Publish khi file chưa ready | Bị chặn |
| T-26 | Publish đồng thời hai tab | Một commit hợp lệ, conflict rõ |
| T-27 | Rollback nội dung | Không đổi model/quyền đã thu hồi |
| T-28 | Thu hồi tài liệu giữa lúc generate | Final answer không dùng nguồn bị thu hồi |
| T-29 | Metadata hiệu lực không rõ/mâu thuẫn | Không trả chắc chắn sai |
| T-30 | Không có nguồn | Trả thiếu nguồn, không bịa |
| T-31 | Model tạo evidence ID/URL giả | Validator loại/chặn |
| T-32 | DOCX không pagination | Không bịa số trang |
| T-33 | Query tiếng Việt không dấu/lỗi gõ | Retrieval được đo trên fixture |
| T-34 | Website mới/sửa/xóa/redirect | Version/diff/tombstone đúng |
| T-35 | Website timeout/403 | Không xóa cả Knowledge |
| T-36 | SSRF tới localhost/private/metadata/IPv6 | Bị chặn |
| T-37 | DNS rebinding/redirect ngoài allowlist | Bị chặn tại kết nối |
| T-38 | HTML XSS/source link nguy hiểm | Sanitize/chặn |
| T-39 | Anonymous gọi personal tool | Yêu cầu đăng nhập |
| T-40 | Citizen A biết mã hồ sơ B | Không đọc được B |
| T-41 | Fake issuer/audience/nonce/expired OIDC | Từ chối |
| T-42 | Gửi Action chưa confirm | Không gọi upstream |
| T-43 | Confirm nonce hết hạn/dùng lại | Từ chối |
| T-44 | Sửa payload sau confirm | Hash mismatch, yêu cầu xác nhận mới |
| T-45 | Double-click confirm cùng payload | Tối đa một execution hợp lệ |
| T-46 | Upstream write timeout sau tiếp nhận | Outcome unknown; không gửi lại mù |
| T-47 | Playground chạy write tool | Dry-run, không gọi production |
| T-48 | API nghiệp vụ chưa cấu hình | Báo chưa tích hợp, không fake success |
| T-49 | Provider 429/timeout/invalid model | Retry giới hạn, lỗi an toàn |
| T-50 | Tool loop quá giới hạn | Dừng, không vượt quota |
| T-51 | Structured output refusal/incomplete | Xử lý đúng trạng thái |
| T-52 | Gửi lại POST message cùng request ID | Trả cùng turn, không nhân chi phí cố ý |
| T-53 | Mất SSE/kết nối lại | Không mất terminal result/không gửi Action lại |
| T-54 | Cancel khi Action đã gửi | Không báo hủy thành công giả |
| T-55 | Nhiều request tiêu budget cùng lúc | Atomic reservation, không race cơ bản |
| T-56 | Không có pricing entry | Hiển thị unknown, không báo 0 |
| T-57 | Production dùng mock/default secrets | Readiness fail |
| T-58 | Purge attachment/chat/document | Bytes/index/cache được xử lý theo policy |
| T-59 | Backup restore | Dữ liệu, RLS, object links, deletion ledger đúng |
| T-60 | UI desktop và mobile | Không tràn, đủ trạng thái, keyboard/focus tốt |
| T-61 | Admin A thử tenant switch/body tenant_id | Không đổi scope |
| T-62 | Thu hồi Action trong phiên đang mở | Không thực thi Action mới |
| T-63 | Attachment user vào public Knowledge | Không tự học/không xuất hiện |
| T-64 | Web search mang thông tin cá nhân | Không gửi query nhạy cảm |
| T-65 | Code sandbox đọc secret host | Không có quyền/mount |
| T-66 | Voice/image capability chưa configured | Không fake output |
| T-67 | Bootstrap lần hai | Không reset dữ liệu/tài khoản |
| T-68 | Docker Engine chưa chạy trên Windows | Dừng với hướng dẫn đúng, không treo |
| T-69 | Model/capability raw fields ở browser response | Không xuất hiện |
| T-70 | Schema API sinh TypeScript | Client typecheck, integration không lệch |

Security fixtures và crawler fixture có thể dùng private hostname trong network test biệt lập với allowlist dành riêng test. Không mang exemption đó sang production.

### 23.3. Bộ đánh giá AI

Tạo ít nhất 50 câu hỏi synthetic ban đầu để chạy regression; trước go-live mở rộng lên bộ 200 câu hỏi hoặc quy mô do đơn vị thống nhất, có review nghiệp vụ.

Mỗi case: tenant, question, expected_behavior, expected_evidence/version, forbidden_content, required_auth, allowed_tools. Có câu hỏi không có đáp án, nguồn mâu thuẫn, văn bản hết hiệu lực, prompt injection và mã hồ sơ của người khác.

Metrics tách biệt: retrieval recall, citation validity, groundedness, độ chính xác nghiệp vụ, từ chối/hỏi rõ đúng, tool authorization, latency và cost. Không dùng cùng một model tự chấm làm chứng cứ duy nhất.

### 23.4. Ngưỡng nghiệm thu đề xuất

- Không chấp nhận lỗi rò tenant, thực thi write trái quyền hoặc lộ secret trong phạm vi bộ test.
- 100% citation hiển thị phải resolve đến nguồn hợp lệ/được phép; không có nguồn bịa.
- Độ chính xác nghiệp vụ trên tập đã được đơn vị chấm: mục tiêu ít nhất 95%; phân loại sai số, không giấu câu khó.
- Test suite bảo mật trọng yếu pass; không có critical/high issue chưa được xử lý hoặc chấp thuận theo quy trình.
- P95 platform overhead mục tiêu dưới 1 giây cho endpoint nhẹ ở tải baseline; tách latency model/OCR/retrieval và báo số đo.
- Kết quả E2E và restore có log/screenshot/thời gian chạy thật.

Các ngưỡng là acceptance targets. Không khẳng định toàn hệ thống không thể bị lỗi chỉ vì test đã pass.


<a id="section-24"></a>

## 24. Dữ liệu mẫu, fixture và demo trung thực

### 24.1. Hai tenant mẫu bắt buộc

`ward-demo-a` và `ward-demo-b`, nhãn “PHƯỜNG MẪU — DỮ LIỆU KIỂM THỬ”. Không tự seed thông tin cơ quan thật, địa chỉ, số điện thoại, mức phí, thời hạn hoặc cán bộ không được người dùng cung cấp.

Hai tenant có cùng tên một thủ tục giả nhưng nội dung khác nhau để kiểm tra isolation. Có một câu trả lời chỉ tồn tại ở tenant B và không được xuất hiện ở A.

### 24.2. Fixture cần tạo

- Văn bản thuần, FAQ có nguồn, PDF text nhiều trang và PDF scan tiếng Việt do dự án tự tạo.
- DOCX có heading/bảng; XLSX nhiều sheet, ô gộp, formula không cache và sheet ẩn.
- PPTX/CSV/HTML nhỏ để kiểm tra parser; file hỏng và loại không hỗ trợ.
- Một tài liệu hết hiệu lực, một bản thay thế, một bản chưa được duyệt công khai.
- Một văn bản có prompt injection và một trang HTML có XSS.
- Website fixture có sitemap, bài mới/sửa/xóa, redirect ra ngoài allowlist và lỗi tạm thời.
- Connector giả lập có success, timeout-before-send, timeout-after-commit, duplicate key, ownership denied.
- Hai citizen test identities ở IdP/test harness; không đưa khóa bypass vào public app.
- Dữ liệu đánh giá với expected evidence IDs và expected authorization behavior.

Tất cả fixture có mô tả rõ là dữ liệu giả. Test tài liệu phải dùng file thật trong fixture, không chỉ mock parser trả chuỗi cố định.

### 24.3. Mock AI

MockAdapter dùng response ổn định theo fixture và trace, phục vụ UI/integration khi thiếu API key. Không giả rằng model thật đã hiểu tài liệu.

UI có banner “MÔI TRƯỜNG THỬ NGHIỆM — CHƯA KẾT NỐI AI THẬT”. Production không cho dùng Mock. Báo cáo chất lượng luôn tách `mock_contract_tests` và `live_ai_evaluation`.

Mock embeddings chỉ phục vụ kiểm tra đường đi dữ liệu; không dùng kết quả đó để nghiệm thu chất lượng vector search. Có lexical retrieval thật ở local để kiểm thử nguồn.

---

<a id="section-25"></a>

## 25. Thứ tự triển khai và Definition of Done từng milestone

Không làm toàn bộ giao diện trước rồi mới thêm backend. Phát triển theo lát cắt chạy xuyên suốt; mỗi milestone có code, migration, tests, UI hoạt động và cập nhật trạng thái.

### M0 — Nền tảng và cách ly

**Làm:** monorepo, dependency locks, Docker, env validation, migrations, TenantContext/RLS, CLI provision, admin auth cơ bản, Mock/OpenAI adapter interfaces, error envelope.

**Chứng minh:** hai tenant thật trong PostgreSQL; app runtime role không đọc chéo; thiếu context không đọc được; production từ chối Mock/secrets mặc định; boot scripts hoạt động hoặc báo rõ môi trường thiếu Docker.

**Chưa gọi là sản phẩm hoàn chỉnh.** Không bỏ test RLS với lý do sẽ làm sau.

### M1 — Lát cắt đầu tiên chạy hoàn chỉnh

**Làm:** Admin login → nhập Knowledge văn bản → lưu nháp → kiểm tra tối thiểu có hiệu lực → publish immutable release → mở trang chat/iframe → hỏi → retrieval từ tài liệu đúng tenant → câu trả lời có nguồn → feedback.

Cả AI adapter thật lẫn Mock phải có đường gọi. Khi không có key, live test ghi not-run; Mock chỉ phục vụ local. Chọn model hoàn toàn từ server.

**Chứng minh:** Playwright flow của Admin A, public A và public B; nguồn khác nhau đúng; tài liệu nháp không lộ; publish/rollback cơ bản an toàn; model field injection bị từ chối.

Đây là ưu tiên sớm nhất để người dùng nhìn được hệ thống đang tiến triển, không phải thu hẹp phạm vi cuối.

### M2 — File Knowledge và RAG đầy đủ

**Làm:** upload, antivirus integration, PDF/DOCX/XLSX/PPTX/TXT/MD/CSV/HTML/ảnh, OCR, review, versioning, pgvector, hybrid retrieval, evidence locator, purge/thu hồi.

**Chứng minh:** fixture thật từng loại, coverage trang/sheet, idempotent worker, permission trước retrieval, false citation bị chặn, bản bị thu hồi không còn dùng.

### M3 — Website, Builder và releases nâng cao

**Làm:** website sync/diff/schedule, Admin screens đầy đủ, Playground trace an toàn, evaluation datasets, preflight publish, optimistic locking, runtime fingerprint revalidation.

**Chứng minh:** sửa website tạo version chờ duyệt; SSRF tests; rollback không khôi phục tài liệu/quyền thu hồi; bộ regression gắn đúng draft hash.

### M4 — Công dân xác thực và Actions

**Làm:** OIDC adapter, top-level personal chat, Action registry/gateway, schema validation, proposals/confirmation, idempotency, outbox execution, reconciliation, dry-run Preview.

**Chứng minh:** ownership checks, double confirm, timeout-after-commit, unknown outcome, không giả lập dữ liệu thật. Nếu chưa có API/IdP thật, sandbox pass nhưng live integration vẫn `blocked_external_dependency`.

### M5 — Các Capabilities còn lại và extensions

**Làm:** Web Search với nguồn hạn chế; attachments; Code Interpreter; image generation; STT/TTS; extension/MCP adapter có kiểm soát.

**Chứng minh:** adapter contract tests, trạng thái not_configured/incompatible đúng, artifact ACL, no secrets, quota. Live smoke tests cho những khả năng Developer đã cấp key/model thật; không đánh dấu toàn bộ verified nếu chỉ có Mock.

### M6 — Quota, usage, analytics và vận hành nội dung

**Làm:** cost ledger, pricing catalog, atomic reservation, dashboard Admin không lộ model, audit, retention jobs, incident pause/revoke.

**Chứng minh:** concurrent quota test, unknown pricing, redaction, purge, budget alerts và developer-only detailed analytics.

### M7 — Hardening, triển khai và kiểm thử hệ thống

**Làm:** MFA production, security scans, browser mobile/accessibility, tải/soak, deployment docs, backup/restore, CI, monitoring/runbooks.

**Chứng minh:** test report có logs; restore có kết quả; không chạy development services ở production; không có endpoint/model secret leak; danh sách rủi ro còn lại được ghi.

### M8 — UAT và sẵn sàng vận hành thật

**Làm:** tích hợp API/IdP thật được cấp, xác nhận domain/hạ tầng/data policy, nạp tri thức đã được phường kiểm duyệt, đánh giá nghiệp vụ, live smoke, thủ tục bàn giao.

**Chứng minh:** go-live gates mục 19.4; UAT sign-off của đơn vị. Nếu chưa có đầu vào bên ngoài thì không thể đánh dấu M8 hoàn tất chỉ bằng mock.

### 25.1. Cách xử lý công việc qua nhiều phiên Codex

Ở mỗi phiên, đọc `IMPLEMENTATION_STATUS.md`, test report và Git diff, tiếp tục task chưa đạt ưu tiên cao nhất. Không hỏi lại “có muốn làm tiếp không” sau từng module trong phạm vi đã được giao.

Khi giới hạn phiên làm việc không cho hoàn thành tất cả, giữ repo chạy được tại milestone hiện tại; ghi `docs/RESUME.md` gồm file đang sửa, tests fail/blocked và task kế tiếp cụ thể. Không báo hoàn thành tổng thể, không để security TODO được lờ đi.

---

<a id="section-26"></a>

## 26. Hồ sơ bàn giao và báo cáo thực thi

### 26.1. Bộ tài liệu Codex phải tạo

| File | Yêu cầu nội dung |
|---|---|
| `README.md` | Sản phẩm, prerequisites, quickstart Windows/Linux, URLs và tài khoản local |
| `AGENTS.md` | Ràng buộc cốt lõi và lệnh quality gates, ngắn gọn |
| `docs/ARCHITECTURE.md` | Module, data flows, tenant trust boundaries |
| `docs/DECISIONS.md` | Quyết định chọn stack/RAG/auth và lý do |
| `docs/DATABASE.md` | ERD, bảng, keys, RLS, migrations, vector profiles |
| `docs/API.md` | OpenAPI location, auth, error, pagination, SSE |
| `docs/SECURITY.md` | Threat model, secrets, privacy, file/crawler/Action controls |
| `docs/ADMIN_GUIDE.md` | Hướng dẫn thao tác từ upload đến publish, không có chọn model |
| `docs/DEPLOYMENT.md` | Docker, TLS/domain, secrets, các phương án hạ tầng |
| `docs/OPERATIONS.md` | Backup/restore, incident, pause/revoke, thay Admin |
| `docs/EXTERNAL_DEPENDENCIES.md` | IdP/API/model/hosting approvals chưa có, tác động |
| `docs/DEPENDENCIES.md` | Version locks, license review, security considerations |
| `docs/IMPLEMENTATION_PLAN.md` | Milestones và task map |
| `docs/IMPLEMENTATION_STATUS.md` | Trạng thái từng REQ/CAP/UI/milestone và bằng chứng |
| `docs/TEST_REPORT.md` | Test thực chạy, command, môi trường, pass/fail/not-run |
| `docs/RESUME.md` | Điểm nối tiếp cho phiên code kế tiếp |

Không tạo document dày chỉ để bù việc chưa có code. Mỗi hạng mục hoàn tất phải trỏ tới source/test/evidence.

### 26.2. Format status

```text
Requirement: REQ-10
Status: implemented_and_tested
Implementation: <paths>
Tests: <test names and actual results>
Limitations: <specific limitations or none>
Next action: <specific action>
```

Các trạng thái cho phép: `not_started`, `in_progress`, `implemented_not_tested`, `implemented_and_tested`, `blocked_external_dependency`. Thêm `live_verified` cho tích hợp đã thử thật; không dùng dấu tick mơ hồ.

### 26.3. Báo cáo cuối mỗi phiên code

Nêu:
- Milestone vừa thực hiện và những file chính thay đổi.
- Các lệnh test đã chạy cùng kết quả; test chưa chạy phải nói chưa chạy.
- Cách mở phần đang hoạt động bằng URL/lệnh cụ thể.
- Phần còn thiếu và phụ thuộc thật.
- Task kế tiếp để tiếp tục từ repo hiện tại.

Không đưa key/password vào báo cáo công khai. Nếu có dữ liệu local cấp lần đầu, chỉ hướng dẫn lấy an toàn trong môi trường local.

---

<a id="section-27"></a>

## 27. Điều kiện không được bỏ qua khi thiếu đầu vào thực tế

| Đầu vào chưa có | Cách phát triển ngay | Cách hiển thị/khóa production |
|---|---|---|
| API key và model ID | Adapter thật + Mock local + contract tests | Không giả live AI; yêu cầu Developer cấu hình |
| Nguồn tài liệu chính thức | Fixture tự tạo, label demo | Không publish fixture như thông tin phường |
| Website/CMS cụ thể | Generic connector + website fixture | Admin chỉ dùng domain đã được Developer cấp |
| IdP chính thức | OIDC adapter + test IdP | Personal mode không hoạt động nếu chưa cấu hình |
| API trạng thái hồ sơ | Connector contract + fixture sandbox | Báo chưa tích hợp, không kết quả giả |
| API gửi phản ánh/đặt lịch | Proposal/execution framework + sandbox | Không gửi đến endpoint đoán ra |
| Hosting/domain/cert | Local Compose + production templates | Không tự public máy phát triển |
| Phê duyệt dữ liệu cá nhân | Data minimization + gates | Không xử lý hồ sơ thật qua provider ngoài |
| Pricing/cost limits | Metering + catalog interface | Unknown pricing rõ ràng; policy do Developer chốt |

Các đầu vào này không ngăn việc xây codebase, nhưng ảnh hưởng việc kiểm thử thật và go-live. Phân biệt **code đã triển khai**, **đã được cấu hình**, **đã kiểm thử live** và **đã được chấp thuận vận hành**.

---

<a id="section-28"></a>

## 28. Checklist tự rà soát trước khi Codex kết thúc

- [ ] Đọc hết đặc tả và cập nhật plan/status, không chỉ đoạn đầu.
- [ ] Model/provider/AI keys chỉ nằm ở technical config, không ở Admin DTO/UI.
- [ ] Chạy được ít nhất lát cắt M1 nếu đang bàn giao giai đoạn đầu.
- [ ] Có hai tenant và test không đọc chéo bằng PostgreSQL runtime role.
- [ ] Admin upload/nhập văn bản tạo tri thức thật, không chỉ lưu tên file.
- [ ] Draft và published phân biệt; nguồn dẫn đúng version/locator.
- [ ] Thu hồi/rollback/permissions không tạo lỗ hổng truy cập dữ liệu cũ.
- [ ] Actions không ghi khi chưa xác thực/xác nhận.
- [ ] Timeout ghi có unknown/reconciliation, không retry mù.
- [ ] Mock và dữ liệu mẫu được ghi nhãn, bị chặn production.
- [ ] Provider adapters có xử lý errors/refusal/usage, không hardcode model.
- [ ] File/crawler/extension không cho thực thi code hoặc SSRF tùy ý.
- [ ] Đã chạy lint/typecheck/tests thực sự, hoặc ghi lý do chưa chạy.
- [ ] Có lệnh startup cho Windows/Linux và URL đúng cấu hình.
- [ ] Không có secret trong Git diff, .env.example, bundle và test reports.
- [ ] Báo cáo trạng thái trung thực, có task tiếp theo cụ thể.

**Quy tắc kết luận:** Chỉ ghi “sẵn sàng vận hành chính thức” khi M0–M8 và go-live gates đạt. Hoàn tất một scaffold hoặc một luồng demo không tương đương hoàn tất hệ thống.

---

<a id="section-29"></a>

## 29. Prompt khởi động có thể gửi nguyên văn cho Codex

```text
Hãy đọc toàn bộ file CODEX_CHATBOT_DA_PHUONG_MASTER_SPEC.md trong workspace
và bắt đầu triển khai phần mềm theo đặc tả, không chỉ đưa ra kế hoạch.

Trước tiên kiểm tra repository hiện tại, AGENTS.md và các thay đổi chưa commit;
không ghi đè hoặc xóa dữ liệu của tôi. Tạo kế hoạch và bảng theo dõi trạng thái,
sau đó thực hiện M0 và lát cắt M1 chạy xuyên suốt, tiếp tục các milestone theo
thứ tự khi điều kiện cho phép.

Ràng buộc tuyệt đối: Admin từng phường không có quyền xem/chọn/thay đổi model,
provider hay API key. Toàn bộ cấu hình AI do Developer đặt ở backend/hạ tầng.
Admin chỉ quản lý Instructions, Knowledge, Capabilities/Actions được cấp,
Preview và Publish.

Ưu tiên code thật có database, API, UI và tests; không làm UI tĩnh hoặc hàm
trả success giả. Thiếu key/API nghiệp vụ thì dùng adapter/fixture được ghi
nhãn trong local và khóa phần chưa được cấu hình ở production.

Sau khi code, chạy các kiểm thử thực tế, sửa lỗi, cập nhật tài liệu và cho
tôi các lệnh chạy trên Windows PowerShell. Báo rõ phần hoàn thành, phần chưa
hoàn thành và test chưa chạy. Không yêu cầu tôi chốt lại các quyết định đã
được ghi trong đặc tả.
```

---

<a id="section-30"></a>

## 30. Nguồn kỹ thuật và cách sử dụng nguồn

Các nguồn dưới đây được đối chiếu ngày **10/11/2026**. Chúng xác nhận hợp đồng/cơ chế của nhà cung cấp; các lựa chọn kiến trúc, ngưỡng, schema nội bộ và milestone trong tài liệu là thiết kế riêng cho dự án, không phải tuyên bố của nhà cung cấp.

Khi viết code, Codex phải kiểm tra lại tài liệu tương ứng với SDK/model/version thực tế rồi khóa dependency. Không sao chép ví dụ có model name từ tài liệu thành lựa chọn cho Admin phường.

| Mã | Tài liệu chính thức | Dùng để kiểm tra |
|---|---|---|
| R01 | [Codex: AGENTS.md][R01] | Hướng dẫn repository, giới hạn và cách đọc |
| R02 | [OpenAI: Responses API][R02] | Output items, request/response và tools |
| R03 | [OpenAI: Function calling][R03] | Schema, strict mode, call IDs |
| R04 | [OpenAI: Structured Outputs][R04] | Schema output, refusal, các giới hạn |
| R05 | [OpenAI: Data controls][R05] | Retention, store, endpoint/capability policies |
| R06 | [OpenAI: File Search][R06] | Hosted retrieval và các định dạng hỗ trợ |
| R07 | [OpenAI: Web Search][R07] | Domain filtering, sources/annotations |
| R08 | [OpenAI: Code Interpreter][R08] | Hosted sandbox/container |
| R09 | [OpenAI: Image generation tool][R09] | Tạo ảnh qua API/tool |
| R10 | [PostgreSQL 17: Row Security Policies][R10] | RLS, owner/superuser/BYPASSRLS |
| R11 | [pgvector: README chính thức][R11] | Dimensions, vector search, filtering/ANN |
| R12 | [Node.js: Releases][R12] | LTS và vòng đời runtime |
| R13 | [OWASP: SSRF Prevention][R13] | URL validation, DNS/redirect/egress |
| R14 | [OpenAI: Speech to text][R14] | Transcription API |
| R15 | [OpenAI: Text to speech][R15] | TTS và yêu cầu sử dụng |
| R16 | [OpenAI: MCP servers][R16] | Tools bên ngoài, approvals/trust |
| R17 | [OpenAI: API pricing][R17] | Rate card khi cấu hình thật |
| R18 | [Docker: Compose in production][R18] | Development/production configuration |

[R01]: https://developers.openai.com/codex/guides/agents-md
[R02]: https://developers.openai.com/api/reference/responses/overview
[R03]: https://developers.openai.com/api/docs/guides/function-calling
[R04]: https://developers.openai.com/api/docs/guides/structured-outputs
[R05]: https://developers.openai.com/api/docs/guides/your-data
[R06]: https://developers.openai.com/api/docs/guides/tools-file-search
[R07]: https://developers.openai.com/api/docs/guides/tools-web-search
[R08]: https://developers.openai.com/api/docs/guides/tools-code-interpreter
[R09]: https://developers.openai.com/api/docs/guides/tools-image-generation
[R10]: https://www.postgresql.org/docs/17/ddl-rowsecurity.html
[R11]: https://github.com/pgvector/pgvector
[R12]: https://nodejs.org/en/about/previous-releases
[R13]: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
[R14]: https://developers.openai.com/api/docs/guides/speech-to-text
[R15]: https://developers.openai.com/api/docs/guides/text-to-speech
[R16]: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
[R17]: https://developers.openai.com/api/docs/pricing
[R18]: https://docs.docker.com/compose/how-tos/production/

---

**Tóm tắt quyết định cuối:** Xây nền tảng chatbot đa phường có Admin Builder,
Knowledge versioning/RAG, Capabilities, Action Gateway và vận hành production.
Admin phường quản lý nội dung và tri thức; Developer quản lý công nghệ AI.
Không thay đổi ranh giới này trong bất kỳ bước triển khai nào.
