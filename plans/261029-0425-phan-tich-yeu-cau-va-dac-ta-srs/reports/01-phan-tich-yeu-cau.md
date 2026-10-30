# Báo cáo phân tích yêu cầu và kiểm thử tài liệu nguồn (Phase 1)

**Dự án:** Phân hệ Caching bài viết và Quản lý phiên (Đề tài 06 — NoSQL)  
**Tác giả phân tích:** SV2 — Nguyễn Anh Quân  
**Ngày lập:** 29/10/2026  
**Mã commit nguồn tham chiếu:** `dd9d242` (nhánh `develop`)

---

## 1. Danh sách yêu cầu nguồn từ Đề bài 06 (DB-01 … DB-19)

Trích dẫn nguyên văn từ tài liệu gốc `docs/ĐỀ TÀI 06.docx` (tổng 26 đoạn, trích xuất qua `word/document.xml`).
Mọi câu trích nằm nguyên vẹn trong cặp dấu ngoặc kép `"..."`.

| ID | Trích nguyên văn (một đoạn con) | Điểm | Vị trí trong đề bài |
|---|---|---|---|
| DB-01 | "Trang tin tức trực tuyến có phân hệ đăng nhập, đọc bài viết; hệ thống tích hợp bộ nhớ đệm để tăng tốc độ tải trang." | — | Đoạn 4: Yêu cầu sản phẩm |
| DB-02 | "Hệ quản trị CSDL chính: Redis (Phối hợp MongoDB / MySQL làm DB gốc)" | — | Đoạn 2: Hệ quản trị CSDL chính |
| DB-03 | "Trình bày rõ nguyên lý hoạt động của kiến trúc bộ nhớ đệm Cache-Aside Pattern." | 1.0 | Đoạn 7: Barem 1. Báo cáo & Thiết kế CSDL (mục 1.0đ) |
| DB-04 | "Thiết kế mô hình dữ liệu Hashes cho Session, Strings/Hashes cho Cache bài viết và cơ chế khóa." | 1.5 | Đoạn 8: Barem 1. Báo cáo & Thiết kế CSDL (mục 1.5đ) |
| DB-05 | "Đăng ký/đăng nhập" | phần 2: 2.5 chung | Đoạn 9: Barem 2. Chức năng CRUD Nền tảng (2.5đ) |
| DB-06 | "viết bài mới, sửa/xóa bài viết trên CSDL chính" | phần 2: 2.5 chung | Đoạn 9: Barem 2. Chức năng CRUD Nền tảng (2.5đ) |
| DB-07 | "Nếu Cache Miss thì gọi DB gốc rồi ghi ngược lại Redis kèm TTL (EXPIRE)." | phần 3: 2.5 chung | Đoạn 11: Barem 3. Chức năng nâng cao đặc trưng (2.5đ) |
| DB-08 | "Khi sửa bài viết, tự động xóa Cache liên quan (Cache Invalidation)." | phần 3: 2.5 chung | Đoạn 11: Barem 3. Chức năng nâng cao đặc trưng (2.5đ) |
| DB-09 | "Dùng cấu trúc Hashes lưu Session người dùng" | phần 3: 2.5 chung | Đoạn 12: Barem 3. Chức năng nâng cao đặc trưng (2.5đ) |
| DB-10 | "dùng lệnh INCR xử lý bộ đếm lượt xem bài viết tăng tiến thời gian thực." | phần 3: 2.5 chung | Đoạn 12: Barem 3. Chức năng nâng cao đặc trưng (2.5đ) |
| DB-11 | "Tối thiểu 100 Bài viết hoàn chỉnh có tiêu đề, nội dung và hình ảnh." | 1.0 chung với DB-12 | Đoạn 17: Định mức Dummy Data — Database gốc |
| DB-12 | "Tối thiểu 20–50 Session/Cache Keys lưu tại Redis có thiết lập TTL khác nhau." | 1.0 chung với DB-11 | Đoạn 18: Định mức Dummy Data — Redis |
| DB-13 | "SV3 mở tab Network (F12) tải bài viết lần 1 (đọc DB gốc ~200ms) vs lần 2 (đọc Redis <5ms)." | 1.5 chung (demo) | Đoạn 24: Kịch bản demo sống bước 1 |
| DB-14 | "SV2 chứng minh Cache cũ bị xóa ngay lập tức (Cache Invalidation)." | 1.5 chung (demo) | Đoạn 25: Kịch bản demo sống bước 2 |
| DB-15 | "SV3 mở Redis Insight chỉ ra Key Session tự động đếm lùi thời gian sống (TTL)." | 1.5 chung (demo) | Đoạn 26: Kịch bản demo sống bước 3 |
| DB-16 | "đo lường và vẽ biểu đồ so sánh thời gian tải qua tab Network F12 / Apache Benchmark" | — | Đoạn 22: Phân công công việc SV3 |
| DB-17 | "Thực hiện trơn tru các bước trong kịch bản demo bảo vệ." | 1.5 | Đoạn 15: Barem 4. Kiểm thử hiệu năng & Demo trực quan (1.5đ) |
| DB-18 | "Thiết kế cấu trúc DB gốc và mô hình Hashes/Strings trên Redis; viết API CRUD bài viết trên DB gốc." | — | Đoạn 20: Phân công công việc SV1 |
| DB-19 | "Xây dựng Middleware Cache-Aside, xử lý TTL (EXPIRE), Cache Invalidation và bộ đếm INCR." | — | Đoạn 21: Phân công công việc SV2 |

*Ghi chú về kiểm tra C11*:
- Đề bài có 26 đoạn văn.
- Tiêu đề được miễn: Đoạn 1 (tên đề tài), Đoạn 5 (`1. BAREM ĐÁNH GIÁ CHI TIẾT...`), Đoạn 6 (`1. Báo cáo & Thiết kế CSDL (2.5đ):`), Đoạn 10 (`3. Chức năng nâng cao đặc trưng (2.5đ):`), Đoạn 13 (`4. Kiểm thử hiệu năng & Demo trực quan (2.5đ):`), Đoạn 16 (`2. QUY ĐỊNH ĐỊNH MỨC BỘ DỮ LIỆU MẪU...`), Đoạn 19 (`3. PHÂN CÔNG CÔNG VIỆC NHÓM 3 SINH VIÊN`), Đoạn 23 (`4. KỊCH BẢN DEMO SỐNG BẢO VỆ`).
- Hai đoạn nội dung được miễn kiểm tra trích dẫn DB theo quy định:
  1. "Số lượng thành viên: 03 sinh viên" (Đoạn 3).
  2. "1.0đ (Dummy Data): Bộ dữ liệu mẫu đạt chuẩn định mức bên dưới." (Đoạn 14).
- Toàn bộ 16 đoạn nội dung còn lại đều được phủ bởi ít nhất một mã DB-01 … DB-19.

---

## 2. Bảng phân tích 37 Ticket Jira CSV (`docs/nosql-jira-tasks.csv`)

CSV gồm 37 ticket từ `SCRUM-13` đến `SCRUM-49`. Bảng đối chiếu trạng thái ghi trong CSV với bằng chứng hiện hữu trong repo mã nguồn:

| Key | Tên công việc (CSV) | Phụ trách | Trạng thái CSV | DB liên quan | Yêu cầu SRS | Bằng chứng trong repo (`file:line` hoặc commit) |
|---|---|---|---|---|---|---|
| SCRUM-13 | API dang ky, dang nhap, dang xuat | Nhu (SV1) | Done | DB-05 | FR-01, FR-02, FR-04, FR-22 | `src/NewsCacheSession.Api/Controllers/AuthController.cs:22,109,165,181`, commit `9aa060e` |
| SCRUM-14 | Luu session bang Redis Hashes + EXPIRE | Quan (SV2) | Done | DB-09 | FR-02, DR-02 | `src/NewsCacheSession.Api/Services/RedisSessionService.cs:16-56`, commit `8d7488a`, `c8431bf` |
| SCRUM-15 | Middleware xac thuc + sliding expiration | Quan (SV2) | Done | DB-09 | FR-03 | `src/NewsCacheSession.Api/Middleware/SessionAuthMiddleware.cs:17-57`, commit `43b1aa5`, `c8431bf` |
| SCRUM-16 | API tao va sua bai viet | Nhu (SV1) | Done | DB-06 | FR-06, FR-07 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:247,381`, commit `9977987` |
| SCRUM-17 | API xoa bai viet (soft delete) | Nhu (SV1) | Done | DB-06 | FR-08 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:461`, commit `eaa879c`, `bcb87e0` |
| SCRUM-18 | API danh sach bai viet: phan trang + loc chuyen muc | Nhu (SV1) | Done | DB-01, DB-06 | FR-09, FR-11 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:81`, `Controllers/CategoriesController.cs:21`, commit `fac2e8e`, `4eea535` |
| SCRUM-19 | API chi tiet bai viet theo slug (ban chua cache) | Nhu (SV1) | Done | DB-01 | FR-10 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:217`, commit `37923a7` |
| SCRUM-20 | Wrapper cache client + hook do metrics | Quan (SV2) | Done | DB-04 | FR-12, FR-19 | `src/NewsCacheSession.Api/Services/RedisCacheService.cs:15`, `Services/ICacheService.cs:5`, commit `fecb48e` |
| SCRUM-21 | Hien thuc luong Cache-Aside cho doc bai viet | Quan (SV2) | Done | DB-07 | FR-12 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:141`, commit `fecb48e`, `cd71517` |
| SCRUM-22 | Layout chung + trang chu danh sach tin | Dinh (SV3) | Done | DB-01 | IR-01 | `src/frontend/src/pages/HomePage.jsx:7`, `src/frontend/src/components/Navbar.jsx`, commit `33fe7eb` |
| SCRUM-23 | Cache Invalidation khi sua/xoa bai viet | Quan (SV2) | Done | DB-08 | FR-14, FR-07, FR-08 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:445,493`, commit `ab0e5d4`, `fc09aee` |
| SCRUM-24 | Co che khoa chong cache stampede (SET NX PX) | Quan (SV2) | Done | DB-04 | FR-13, NFR-03 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:161-200`, `Services/RedisCacheService.cs:84-100`, commit `fecb48e`, `5ef3e56` |
| SCRUM-25 | Bo dem luot xem realtime bang INCR + job flush ve MongoDB | Quan (SV2) | Done | DB-10 | FR-17, FR-18 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:505`, `Services/ViewCountSyncWorker.cs:15`, commit `f9babea`, `7ecc3d5`, `f9ad132` |
| SCRUM-26 | Cache danh sach trang chu voi TTL ngan | Quan (SV2) | Done | DB-07, DB-08 | FR-15, FR-16 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:81-137`, commit `ef43a20`, `13187b7`, `d2bcb27` |
| SCRUM-27 | Trang chi tiet bai viet + luot xem realtime | Dinh (SV3) | Done | DB-01, DB-10 | IR-02 | `src/frontend/src/pages/PostDetailPage.jsx:13`, commit `f98b976` |
| SCRUM-28 | Viet chuong nguyen ly Cache-Aside Pattern | Quan (SV2) | Done | DB-03 | NFR-09 | `docs/bao-cao-nguyen-ly-cache-aside.md:1`, commit `6c988ec` |
| SCRUM-29 | Trang admin CRUD bai viet | Dinh (SV3) | Done | DB-06 | IR-04 | `src/frontend/src/pages/AdminPostsPage.jsx:12`, `src/frontend/src/pages/CreateEditPostPage.jsx:14`, commit `acc9f02`, `163b0e5` |
| SCRUM-30 | Trang dang nhap / dang ky | Dinh (SV3) | Done | DB-05 | IR-03 | `src/frontend/src/pages/LoginPage.jsx:10`, `src/frontend/src/pages/RegisterPage.jsx:10`, commit `1297a35` |
| SCRUM-31 | Trang quan ly phien dang hoat dong | Dinh (SV3) | Done | DB-09, DB-15 | IR-05, FR-05 | `src/frontend/src/pages/AdminSessionsPage.jsx:11`, `src/NewsCacheSession.Api/Controllers/AuthController.cs:202`, commit `37b3f9e`, `f9d0987` |
| SCRUM-32 | Script seed 100+ bai viet that co hinh anh | Dinh (SV3) | Done | DB-11 | DR-03 | `scripts/SeedPosts/seed.py:1`, `scripts/SeedPosts/verify_real.py:1`, commit `85cd9e8`, `fa95e49` |
| SCRUM-33 | Viet chuong thiet ke mo hinh du lieu Redis + co che khoa | Nhu (SV1) | In Progress | DB-04 | DR-01, DR-02, FR-13 | `docs/redis-keyspace.md:1`, `docs/mongodb-schema.md:1`, `docs/chot-thiet-ke-sv1.md:1`, commit `4c9a9c9`, `858d0e4` |
| SCRUM-34 | Endpoint /cache/stats cho ty le hit/miss | Quan (SV2) | Done | DB-16 | FR-19 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:532`, commit `fecb48e`, `9d4c596` |
| SCRUM-35 | Test tu dong cho Cache Invalidation | Quan (SV2) | Done | DB-08, DB-14 | NFR-08 | `tests/NewsCacheSession.Tests/Integration/CacheInvalidationTests.cs:17`, commit `ab0e5d4`, `f98443b` |
| SCRUM-36 | Script seed 20-50 session/cache key voi TTL khac nhau | Dinh (SV3) | Done | DB-12 | DR-03 | `scripts/SeedRedis/seed_redis.py:1`, `scripts/SeedRedis/verify_seed_redis.py:1`, commit `bdf416f` |
| SCRUM-37 | Test tu dong cho TTL va session expiry | Quan (SV2) | Done | DB-09, DB-15 | NFR-08 | `tests/NewsCacheSession.Tests/Integration/SessionLifecycleTests.cs:17`, `SessionExpiryTests.cs:12`, commit `ab0e5d4` |
| SCRUM-38 | Badge hien thi CACHE HIT/MISS va response time tren UI | Dinh (SV3) | Done | DB-13 | IR-02 | `src/frontend/src/components/CacheStatusBadge.jsx:1`, commit `b2adb96` |
| SCRUM-39 | Upload va quan ly hinh anh bai viet | Dinh (SV3) | Idea | DB-11 | FR-21 | Đã hoàn thành trong code: `src/NewsCacheSession.Api/Controllers/ImagesController.cs:7,20`, `src/NewsCacheSession.Api/Services/CloudinaryImageStorageService.cs:22`, commit `c60caf6`, `2591111` |
| SCRUM-40 | Benchmark Apache Bench / k6: lan 1 vs lan 2 | Dinh (SV3) | Idea | DB-16 | NFR-01, NFR-02 | Đã hoàn thành: `scripts/Benchmark/benchmark.py:1`, `scripts/Benchmark/results/2026-10-25-chinh-thuc/summary.json`, commit `c72a68f` |
| SCRUM-41 | Ve bieu do so sanh thoi gian tai + bang so lieu | Dinh (SV3) | Idea | DB-16 | NFR-04 | Đã hoàn thành: `scripts/Benchmark/plot.py:1`, `scripts/Benchmark/results/2026-10-25-chinh-thuc/charts/`, commit `0a26a51`, `aadfee1` |
| SCRUM-42 | Viet chuong kiem thu hieu nang | Dinh (SV3) | Idea | DB-16 | NFR-09 | Đã hoàn thành: `docs/bao-cao-kiem-thu-hieu-nang.md:1`, commit `e9c7155` |
| SCRUM-43 | Kiem thu hoi quy toan he thong truoc demo | Dinh (SV3) | Idea | DB-17 | NFR-08 | Đã hoàn thành: `plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/`, commit `dd9d242`, `46098a7` |
| SCRUM-44 | Slide + kich ban demo song 3 buoc theo de | Dinh (SV3) | Idea | DB-17 | NFR-09 | Đã soạn kịch bản: `docs/kich-ban-demo-va-do-hieu-nang.md:1`, `docs/phan-cong-va-kich-ban-demo.md:1` |
| SCRUM-45 | Tong duyet demo 2 luot + quay video du phong | Dinh (SV3) | Idea | DB-17 | NFR-09 | Đã diễn tập 2 lượt: `plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/reports/03-e2e-va-dien-tap.md:1` |
| SCRUM-46 | Checklist doi chieu barem 10 diem | Nhu (SV1) | Done | DB-17 | NFR-09 | `docs/checklist-barem.md:1`, commit `4bbde68` |
| SCRUM-47 | Ra soat README + huong dan cai dat tu dau | Nhu (SV1) | In Progress | DB-01 | NFR-09 | Đã rà soát: `README.md:1`, `docs/ra-soat-cai-dat-tu-dau.md:1`, commit `b043f94`, `d33f94d` |
| SCRUM-48 | Dong goi va NOP DO AN NOSQL | Nhu (SV1) | Idea | DB-17 | NFR-09 | Chưa nộp đồ án (đang trong giai đoạn chuẩn bị báo cáo SRS v3.0 và đóng gói) |
| SCRUM-49 | Chuan bi cau hoi phan bien va cau tra loi | Ca nhom | Idea | DB-17 | NFR-09 | Nội dung phân biện chuẩn bị theo kịch bản bảo vệ và barem đối chiếu |

---

## 3. Bảng quyết định xử lý mâu thuẫn tài liệu nguồn (S1–S10) và Barem (D24)

| # | Mâu thuẫn | Nguồn A | Nguồn B | Quyết định | Lý do kỹ thuật & Dẫn chứng |
|---|---|---|---|---|---|
| S1 | Tải lần 1 vs lần 2: Đề bài ghi "~200ms vs <5ms", số đo thật "8,74 ms vs 2,96 ms" | Đề bài 06 đoạn 24 | `scripts/Benchmark/results/2026-10-25-chinh-thuc/summary.json` | Trích nguyên văn đề bài ở DB-13; tiêu chí kỹ thuật chấp nhận ở NFR-01/02 là HIT ≤ 5 ms, HIT < MISS, header `X-Cache` đổi MISS → HIT | MongoDB local warm cache đọc NVMe cực nhanh (~3–8 ms), không có độ trễ mạng Internet nên không đạt tới mức 200 ms. Đã giải thích cặn kẽ tại `docs/bao-cao-kiem-thu-hieu-nang.md` §5.2 |
| S2 | Đề bài ghi SV2 làm "Middleware Cache-Aside", code thực tế đặt trong Controller | Đề bài 06 đoạn 21 | `src/NewsCacheSession.Api/Controllers/PostsController.cs:141` | Giữ câu trích DB-19; giải thích trong SRS lý do thiết kế đặt Cache-Aside tại Controller | Chỉ endpoint `GET /api/posts/{id}` cần cache; endpoint slug cố ý không cache làm đối chứng; Cache-Aside cần can thiệp logic dữ liệu DTO nên đặt tại Controller phù hợp hơn Middleware |
| S3 | Đề bài cho phép "Strings/Hashes cho Cache bài viết" | Đề bài 06 đoạn 8 | `src/NewsCacheSession.Api/Services/RedisCacheService.cs:40` | Chọn String JSON cho `post:{id}` và `posts:cat:{id}:p{n}:v{ver}` | Đọc bài viết là đọc nguyên đối tượng để trả API JSON. String JSON đơn giản, O(1), không tốn chi phí quản trị hash field (`docs/redis-keyspace.md` §2) |
| S4 | Định mức Redis: "20–50 Session/Cache Keys" là khoảng hay tối thiểu? | Đề bài 06 đoạn 18 | `scripts/SeedRedis/seed_redis.py:91,97,255` | Diễn giải: Tối thiểu 20 key có TTL khác nhau; bộ seed tạo mặc định 40 key | 40 key gồm 20 session (TTL 300→1800 s) và 20 cache bài (TTL 30→600 s), đảm bảo trong khoảng 20–50 theo yêu cầu |
| S5 | Lệnh khóa phân tán: CSV ghi `SET NX PX`, keyspace ghi `NX EX 5`, checklist ghi `NX PX 5000` | CSV (SCRUM-24) | `docs/redis-keyspace.md`, `Services/RedisCacheService.cs:84` | Khóa phân tán TTL 5 giây cấp bằng `LockTakeAsync` (`SET key val NX EX/PX`) | Đều là cơ chế phân tán nguyên tử với TTL 5 giây. Lệnh chính xác gửi tới Redis được kiểm chứng thực tế bằng `MONITOR` ở Phase 4 |
| S6 | CSV Jira gối ngày: Sprint 1 (23–24 Sep) chồng ngày lên Sprint 2 (23–29 Sep) | `docs/nosql-jira-tasks.csv` | Lịch trình Scrum tuần tự | Giữ nguyên văn giá trị CSV trong bảng ma trận Jira; giải thích tại Phụ lục F | Dữ liệu xuất trực tiếp từ Jira, không được tự ý sửa file CSV để đảm bảo tính nguyên bản |
| S7 | 11 Ticket CSV ở trạng thái Idea/In Progress nhưng repo đã có kết quả thực tế | `docs/nosql-jira-tasks.csv` | Git commits và mã nguồn thực tế | Giữ cột "Trạng thái CSV", bổ sung cột "Bằng chứng trong repo" | Phản ánh trung thực trạng thái Jira xuất ra, đồng thời chứng minh tiến độ thực tế bằng commit hash và đường dẫn file |
| S8 | Đề bài nêu "MongoDB / MySQL làm DB gốc" | Đề bài 06 đoạn 2 | `src/NewsCacheSession.Api/Data/MongoContext.cs:1` | Chọn MongoDB làm DB gốc | MongoDB là Document Database chuẩn NoSQL, phối hợp tự nhiên với cấu trúc JSON và Redis |
| S9 | `AGENTS.md` §6 và `checklist-barem.md` ghi nhận lạc hậu | `AGENTS.md` §6, `checklist-barem.md:22,128` | Mã nguồn thực tế đã hoàn tất | SRS v3 phản ánh sự thật từ mã nguồn; không tự ý sửa file của thành viên khác; lập báo cáo thông báo ở Phase 4 | Tuân thủ tuyệt đối quy định phân công và quyền sở hữu file của nhóm |
| S10 | Đề bài nhắc "Apache Benchmark", nhóm đo bằng `scripts/Benchmark/benchmark.py` | Đề bài 06 đoạn 22 | `scripts/Benchmark/benchmark.py:1` | Nêu rõ công cụ `benchmark.py` thay thế và trình bày lý do | `benchmark.py` tự viết bằng Python chuẩn, hỗ trợ đo kịch bản Cache-Aside phân luồng chính xác, tính P50/P95/P99 và xuất JSON tự động tích hợp CI/CD (`scripts/Benchmark/README.md:12`) |
| D24 | SRS v2.0 tự ý chia điểm con phần 2 (1.0/1.5) và phần 3 (1.25/1.25) | Đề bài 06 đoạn 9, 10–12 | `docs/SRS.md:791-795` (v2.0) | SRS v3 giữ thang điểm 2.5đ chung cho Phần 2 và 2.5đ chung cho Phần 3 | Đề bài không quy định điểm con cho phần 2 và phần 3, việc tự chia điểm con là sai lệch so với đề bài gốc |

---

## 4. Kho yêu cầu SRS v3.0

### 4.1. Yêu cầu chức năng (Functional Requirements: FR-01 … FR-22)

| ID | Tên yêu cầu & Tóm tắt nội dung | Nguồn | Kiểm chứng |
|---|---|---|---|
| FR-01 | Đăng ký tài khoản: mật khẩu BCrypt, admin đầu tiên giành bằng `meta._id = bootstrapAdmin`, trùng username trả 409 | DB-05, SCRUM-13 | T |
| FR-02 | Đăng nhập: tạo phiên Redis Hash 5 field + `EXPIRE` trong một giao dịch `MULTI/EXEC`, trả cookie `SessionId` | DB-05, DB-09, SCRUM-13, SCRUM-14 | T |
| FR-03 | Middleware xác thực phiên: đọc cookie `SessionId` hoặc header `X-Session-Id`, sliding TTL, cấp lại cookie | DB-09, SCRUM-15 | T |
| FR-04 | Đăng xuất: xóa key `session:{sessionId}` khỏi Redis | DB-05, SCRUM-13 | T |
| FR-05 | Quản trị phiên: admin liệt kê phiên (SCAN phân trang) và thu hồi phiên người dùng; chặn tự thu hồi phiên mình | DB-15, SCRUM-31 | T, D |
| FR-06 | Tạo bài viết: slug tiếng Việt chuẩn, xử lý trùng slug `-2, -3…` (thử ≤ 3 lần), `INCR posts:ver` | DB-06, SCRUM-16 | T |
| FR-07 | Sửa bài viết: kiểm tra quyền admin/tác giả, giữ slug, ghi MongoDB trước rồi `DEL post:{id}` + `INCR posts:ver` | DB-06, DB-08, SCRUM-16, SCRUM-23 | T |
| FR-08 | Xóa bài viết (xóa mềm `isDeleted = true`), xóa cache `DEL post:{id}` + `INCR posts:ver`, giữ nguyên bộ đếm lượt xem | DB-06, DB-08, SCRUM-17, SCRUM-23 | T |
| FR-09 | Danh sách bài viết: phân trang `page`, `pageSize` 1–50 (mặc định 10), lọc theo `categoryId` | DB-01, SCRUM-18 | T |
| FR-10 | Đọc bài viết theo slug (`GET /api/posts/slug/{slug}`): cố ý không cache làm mốc đối chứng | DB-01, DB-13, SCRUM-19 | T |
| FR-11 | Quản lý chuyên mục: 3 endpoint đọc (danh sách, theo id, theo slug) + tạo chuyên mục (admin) | DB-06, SCRUM-18 | T, I |
| FR-12 | Cache-Aside khi đọc bài viết (`GET /api/posts/{id}`): TTL 600 s, trả header `X-Cache: HIT` hoặc `MISS` | DB-07, SCRUM-20, SCRUM-21 | T |
| FR-13 | Khóa chống Cache Stampede: khóa phân tán `lock:post:{id}` TTL 5 s, thử lại 40 × 50 ms rồi fallback Mongo | DB-04, SCRUM-24 | T |
| FR-14 | Vô hiệu hóa Cache (Cache Invalidation): tự động xóa `post:{id}` và tăng `posts:ver` khi sửa/xóa bài viết | DB-08, DB-14, SCRUM-23 | T, D |
| FR-15 | Cache danh sách trang chủ: key `posts:cat:{cat\|all}:p{n}:v{ver}`, TTL 180 s; lệch `pageSize` coi là MISS | DB-07, SCRUM-26 | T |
| FR-16 | Quản lý phiên bản danh sách bài viết: `INCR posts:ver` thay cho việc SCAN + DEL toàn bộ danh sách | DB-08, SCRUM-26 | T, I |
| FR-17 | Tăng lượt xem bài viết (`POST /api/posts/{id}/view`): `SET NX` từ Mongo, `INCR`, `SADD posts:dirty_views`, 404 nếu bài không tồn tại | DB-10, SCRUM-25 | T |
| FR-18 | Worker đồng bộ lượt xem (Write-Behind): chu kỳ 60 s, `SCARD` + `SPOP n`, ghi vào MongoDB; lỗi thì trả lại Set | DB-10, SCRUM-25 | T |
| FR-19 | Thống kê hiệu năng Cache (`GET /api/cache/stats`): trả đúng 4 field `hits, misses, totalRequests, hitRate` | DB-16, SCRUM-34 | T |
| FR-20 | Kiểm tra sức khỏe hệ thống: `/health` (Kestrel/Docker) và `/api/health` (trả 503 nếu Mongo hoặc Redis hỏng) | DB-02 | T |
| FR-21 | Tải ảnh bài viết (`POST /api/images`): jpeg/png/webp ≤ 5 MB, gọi REST Cloudinary; cờ `PostingSettings:AdminOnly` | DB-11, SCRUM-39 | T, I |
| FR-22 | Lấy thông tin phiên hiện tại (`GET /api/auth/me`): trả userId, username, role và `expiresInSeconds` | DB-15, SCRUM-13, SCRUM-30 | T |

### 4.2. Yêu cầu giao diện (Interface Requirements: IR-01 … IR-05)

| ID | Tên giao diện & Tóm tắt | Nguồn | Kiểm chứng |
|---|---|---|---|
| IR-01 | Giao diện Trang chủ: lưới bài viết, phân trang 12 bài/trang, bộ lọc chuyên mục, thanh tìm kiếm | DB-01, SCRUM-22 | T (Vitest), D |
| IR-02 | Giao diện Chi tiết bài viết: nội dung, ảnh đại diện, lượt xem realtime, badge `X-Cache` (HIT xanh / MISS vàng) | DB-01, DB-10, DB-13, SCRUM-27, SCRUM-38 | T (Vitest), D |
| IR-03 | Giao diện Đăng nhập / Đăng ký: biểu mẫu xác thực, thông báo lỗi rõ ràng, tự động lưu phiên | DB-05, SCRUM-30 | T (Vitest), D |
| IR-04 | Giao diện Quản trị bài viết: bảng quản trị bài viết, bộ lọc, trình soạn thảo kèm tải ảnh | DB-06, DB-11, SCRUM-29, SCRUM-39 | T (Vitest), D |
| IR-05 | Giao diện Quản trị phiên: bảng danh sách phiên hoạt động, đếm lùi thời gian sống, nút thu hồi phiên | DB-09, DB-15, SCRUM-31 | T (Vitest), D |

### 4.3. Yêu cầu phi chức năng (Non-Functional Requirements: NFR-01 … NFR-09)

| ID | Tên yêu cầu & Tiêu chí định lượng | Nguồn | Kiểm chứng |
|---|---|---|---|
| NFR-01 | Tốc độ Cache HIT: Thời gian phản hồi Cache HIT ≤ 5 ms (kết quả đo chính thức đạt 2,96 ms) | DB-13 | A |
| NFR-02 | Hiệu quả Cache-Aside: HIT nhanh hơn MISS (2,96 ms vs 8,74 ms); kèm tài liệu giải thích độ trễ | DB-13 | A |
| NFR-03 | Khả năng chống Cache Stampede: 50 request đồng thời vào bài viết chưa cache chỉ sinh đúng 1 lượt gọi DB gốc (1 MISS, 49 HIT) | DB-04 | T, A |
| NFR-04 | Năng lực tải đồng thời: Hệ thống chịu tải ≥ 800 req/s ở mức 50 kết nối đồng thời với tỷ lệ lỗi 0% | Mục tiêu nhóm | A |
| NFR-05 | Khả năng chịu lỗi (Resilience): Khi Redis ngừng hoạt động, API đọc bài viết vẫn phục vụ từ MongoDB; API ghi phiên trả 503 | Thiết kế | T |
| NFR-06 | An toàn & Bảo mật: Cookie `SessionId` có cờ `HttpOnly`, `SameSite=Lax`, `Secure` theo giao thức; mã hóa mật khẩu bằng BCrypt | Chuẩn Web | T, I |
| NFR-07 | Tính nhất quán dữ liệu: Ghi CSDL gốc trước, xóa/vô hiệu hóa Redis sau; xóa cache trước khi xóa ảnh Cloudinary | DB-08 | T |
| NFR-08 | Khả năng kiểm thử tự động: Toàn bộ chức năng có unit/integration test tự động; tài liệu có checker kiểm tra | Mục tiêu nhóm | I |
| NFR-09 | Tuân thủ nghiệm thu & Barem: Báo cáo nguyên lý Cache-Aside, phân công 3 SV theo đề bài, kịch bản demo 3 bước chạy trơn tru | DB-03, DB-16, DB-17, DB-18, DB-19 | I, D |

### 4.4. Yêu cầu dữ liệu & Lưu trữ (Data Requirements: DR-01 … DR-03)

| ID | Tên yêu cầu & Định mức | Nguồn | Kiểm chứng |
|---|---|---|---|
| DR-01 | CSDL gốc MongoDB: 4 collection (`posts`, `users`, `categories`, `meta`), tuân thủ camelCase với `[BsonElement]`, 5 index tối ưu | DB-02, DB-06 | I, T |
| DR-02 | Cấu trúc Redis Keyspace: 7 mẫu key chuẩn theo thiết kế (`session:*`, `post:*`, `post:*:views`, `posts:cat:*`, `posts:ver`, `lock:post:*`, `posts:dirty_views`) | DB-04, DB-09, DB-10 | I, T |
| DR-03 | Định mức dữ liệu mẫu (Dummy Data): ≥ 100 bài viết hoàn chỉnh có ảnh và chuyên mục; 20–50 key Redis có TTL khác nhau | DB-11, DB-12 | T, A |

---

## 5. Hợp đồng định dạng tài liệu SRS v3.0

Bộ kiểm tra tài liệu tự động (`scripts/DocCheck/check_srs.py`) ở Phase 2 sẽ bám sát các mẫu cấu trúc sau:

1. **Bảng yêu cầu nguồn**: Mỗi dòng bắt đầu bằng `| DB-NN |`, cột thứ hai chứa trích dẫn nguyên văn trong cặp dấu ngoặc kép `"..."`.
2. **Khối yêu cầu chi tiết**: Tiêu đề có định dạng `##### FR-NN: <Tên>` / `##### NFR-NN: <Tên>` / `##### IR-NN: <Tên>` / `##### DR-NN: <Tên>`. Ngay dưới tiêu đề là bảng thuộc tính:
   ```markdown
   | Thuộc tính | Giá trị |
   |---|---|
   | Nguồn | DB-xx, SCRUM-yy |
   | Ưu tiên | BẮT BUỘC / NÊN / CÓ THỂ |
   | Phụ trách | SVx — Tên |
   | Kiểm chứng | T / D / I / A |
   | Test case | TC-zz |
   ```
   Sau bảng thuộc tính là mục `**Mô tả**` ("Hệ thống PHẢI...") và `**Tiêu chí chấp nhận**`, trong đó mỗi tiêu chí được viết theo cấu trúc:
   - *Cho ...*
   - *Khi ...*
   - *Thì ...*
3. **Danh mục Test Case (Phụ lục E)**: Dòng bảng có dạng `| TC-NN | <T|D|I|A> | <bằng chứng> | <ID yêu cầu> |`. Với loại T, bằng chứng là `` `đường/dẫn/File.cs::MethodName` `` hoặc file test tương ứng.
4. **Ma trận Jira (Phụ lục C.2)**: Bảng đủ 37 dòng: `| SCRUM-NN | <tên> | <phụ trách> | <trạng thái CSV> | <bằng chứng> | <ID yêu cầu> |`.
5. **Bảng Keyspace Redis**: Tiêu đề bảng chứa hai cột `Key` và `TTL`.
6. **Bảng số đo hiệu năng**: Tiêu đề bảng chứa `| Chỉ số | Không cache | Cache MISS | Cache HIT |` và các hàng `Mean`, `P50`, `P95`, `P99`, `Min`.
7. **JSON mẫu thống kê cache**: Khối mã ` ```json ` trong FR-19 chứa đúng 4 key: `hits`, `misses`, `totalRequests`, `hitRate`.
8. **Vùng bỏ qua kiểm tra**: Checker tự động bỏ qua nội dung nằm trong mục "Lịch sử phiên bản" và "Phụ lục F" khi kiểm tra các lỗi nội dung lịch sử.

