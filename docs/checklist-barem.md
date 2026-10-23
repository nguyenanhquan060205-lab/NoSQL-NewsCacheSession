# Checklist đối chiếu barem 10 điểm (SCRUM-46)

**Lập ngày 23/10/2026** — vai nhóm trưởng (SV1). **Hạn nộp: 26/10/2026.**

Thước đo của file này là **barem 4 × 2.5đ trong đề bài gốc** (`docs/ĐỀ TÀI 06.docx`).
`docs/SRS_NewsCacheSession_DeTai06_rutgon.md` là tài liệu định hướng, **không phải
thước đo chấm điểm** — nhóm đã chốt không refactor theo nó (giữ collection `posts`,
quy ước camelCase, một instance Redis).

Mỗi mục ghi **bằng chứng kiểm chứng được** (file + mã commit) và **chỗ còn thiếu**.
Commit tra bằng `git show <hash> --stat`.

---

## Tổng quan

| Phần barem | Điểm | Phụ trách | Trạng thái | Rủi ro mất điểm |
|---|---|---|---|---|
| 1. Báo cáo & Thiết kế CSDL | 2.5 | SV2 (1.0) + **SV1 (1.5)** | 🟡 Gần đủ | 1.5đ của SV1 chưa thành chương báo cáo |
| 2. Chức năng CRUD nền tảng | 2.5 | **SV1** | 🟢 Đủ | Không có test tự động cho CRUD |
| 3. Chức năng nâng cao | 2.5 | SV2 | 🟢 Đủ | — |
| 4. Kiểm thử hiệu năng & Demo | 2.5 | SV3 | 🔴 **Hổng** | **Chưa có số đo, chưa có biểu đồ** |

**Kết luận một dòng:** phần code đã gần đủ điểm; **rủi ro lớn nhất không nằm ở code mà
ở hai tài liệu chưa viết** — chương thiết kế Redis của SV1 (1.5đ) và phần đo hiệu năng
của SV3 (ước 1.0–1.5đ).

---

## Phần 1 — Báo cáo & Thiết kế CSDL (2.5đ)

### 1a. Nguyên lý Cache-Aside — 1.0đ — SV2 🟢

| Bằng chứng | Chi tiết |
|---|---|
| `docs/bao-cao-nguyen-ly-cache-aside.md` | 115 dòng, 5 chương: đặt vấn đề → so sánh chiến lược caching → sơ đồ tuần tự luồng đọc → 4 thách thức (stampede, nhất quán, versioning O(1), INCR write-behind) → kết luận |
| Commit `6c988ec` | `docs(SCRUM-28): báo cáo nguyên lý cache-aside và cập nhật trạng thái jira tasks` |

**Còn thiếu:** mục 5 "Kết Luận & Kết Quả Thực Nghiệm Demo" cần số đo thật từ SV3 —
hiện chưa có số để điền (xem Phần 4).

### 1b. Thiết kế mô hình Hashes/Strings + cơ chế khóa — 1.5đ — SV1 🟡

| Bằng chứng | Chi tiết |
|---|---|
| `docs/redis-keyspace.md` | 111 dòng: bảng keyspace, bảng field trong Hash session, lý giải chọn cấu trúc, lý giải TTL từng loại, luồng Cache-Aside, Cache Invalidation, vì sao dùng số phiên bản |
| `docs/mongodb-schema.md` | 112 dòng: schema 3 collection, quy ước camelCase, bảng index, lập luận reference vs embed |
| `docs/chot-thiet-ke-sv1.md` | 163 dòng: hợp đồng dữ liệu gửi SV2/SV3 |
| Commit `2fbaa8e` | `fix(SCRUM-33): chốt quy ước camelCase cho MongoDB và keyspace Redis` |
| Commit `559fdb8` | `docs: cache danh sách dùng số phiên bản + cập nhật hợp đồng cho SV2/SV3` |
| Code khớp doc | `Models/Post.cs`, `User.cs`, `Category.cs` — mọi property có `[BsonElement]`; `categoryId`/`authorId` có `[BsonRepresentation(BsonType.ObjectId)]` |

**Còn thiếu (đây là việc ưu tiên 1 của SV1):**

- [ ] **Sơ đồ luồng Cache-Aside** — `redis-keyspace.md` hiện **không có một hình nào**
- [ ] **Ảnh chụp RedisInsight làm bằng chứng** — cần 4 ảnh: Hash `session:{id}` đang
      đếm lùi TTL · `post:{id}` TTL 600s · `post:{id}:views` tăng sau khi xem ·
      `posts:ver` tăng sau khi sửa bài
- [ ] **Gộp và định dạng lại thành chương báo cáo** (hiện là 3 file rời viết cho lập trình viên đọc)

> Thầy chấm 1.5đ bằng cách **đối chiếu doc với RedisInsight** — ảnh chụp không phải
> trang trí, nó chính là bằng chứng chấm điểm.

---

## Phần 2 — Chức năng CRUD nền tảng (2.5đ) — SV1 🟢

| Chức năng | File | Commit |
|---|---|---|
| Đăng ký / đăng nhập / đăng xuất / me (BCrypt + session Redis) | `Controllers/AuthController.cs`, `DTOs/Auth/*` | `9aa060e` (SCRUM-13) |
| Danh sách bài: phân trang + lọc chuyên mục, `pageSize` clamp 1–50 | `Controllers/PostsController.cs` `GetAll`, `DTOs/Posts/PagedPostsResponse.cs` | `fac2e8e` (SCRUM-18) |
| Chi tiết theo slug (cố ý **không** cache — mốc đo "trước") | `PostsController.GetBySlug` | `37923a7` (SCRUM-19) |
| Tạo / sửa bài, slug duy nhất, giữ slug khi đổi tiêu đề | `PostsController.Create/Update`, `DTOs/Posts/*` | `9977987` (SCRUM-16) |
| Xóa mềm + Cache Invalidation, **không** xóa bộ đếm views | `PostsController.Delete` | `bcb87e0` (SCRUM-17) |
| Chuyên mục: 3 endpoint đọc công khai + tạo (chỉ admin) | `Controllers/CategoriesController.cs`, `Models/Category.cs` | `4eea535` (SCRUM-18) |
| Phân quyền admin/tác giả cho sửa–xóa | `PostsController.CanModify`, `Services/CurrentUserService.cs` | `163b0e5` (SCRUM-29) |
| Quản lý phiên cho admin (liệt kê bằng `SCAN`, thu hồi phiên) | `Services/RedisSessionQueryService.cs`, `AuthController` | `f9d0987` (SCRUM-31) |
| Index MongoDB tự tạo lúc khởi động (5 index) | `Data/MongoIndexInitializer.cs` | `4eea535` |
| Slug tiếng Việt (xử lý riêng chữ `đ`) | `Utils/SlugHelper.cs` | `163b0e5` |

**Còn thiếu / rủi ro:**

- [ ] **Không có test tự động nào phủ CRUD của SV1.** Bộ xUnit ở `tests/` chỉ phủ phần
      SV2 (cache, session, middleware, worker). Kiểm chứng duy nhất là **54 ca smoke test
      chạy tay qua HTTP ngày 30/09**, và **log/ảnh của lần chạy đó không có trong repo**.
      → Khi báo cáo phải nói đúng là "chạy tay", đừng nói "có bộ test".
- [ ] Chưa chạy lại smoke test trên `main` mới (`b2adb96`) sau khi SV2/SV3 merge 15 commit.

---

## Phần 3 — Chức năng nâng cao: Cache-Aside, Session Hashes, INCR (2.5đ) — SV2 🟢

| Chức năng | File | Commit |
|---|---|---|
| Session lưu bằng Redis **Hash** + TTL 30 phút | `Services/RedisSessionService.cs` | `c8431bf` (SCRUM-14) |
| Middleware sliding expiration | `Middleware/SessionAuthMiddleware.cs` | `c8431bf` (SCRUM-15) |
| Cache-Aside + khóa chống stampede (`SET NX PX 5000`) | `PostsController.GetById`, `Services/RedisCacheService.cs` | `fecb48e` (SCRUM-21/20/24/34) |
| Endpoint thống kê cache (hit/miss) | `Controllers/CacheStatsController.cs` | `fecb48e` |
| Bộ đếm lượt xem `INCR` + worker write-behind | `PostsController.IncrementView`, `Services/ViewCountSyncWorker.cs` | `f9babea` (SCRUM-25) |
| Cache danh sách theo số phiên bản (TTL 3 phút) | `PostsController.GetAll` | `ef43a20` (SCRUM-26) |
| Test tự động (xUnit + Moq + FluentAssertions) | `tests/NewsCacheSession.Tests/` — 6 file test | `ab0e5d4` (SCRUM-35/37) |

**Lưu ý khi demo:** `tests/NewsCacheSession.Tests.csproj` nhắm `net10.0` còn API nhắm
`net8.0`. Máy chỉ có SDK 9 sẽ **fail ngay lúc build** (`NETSDK1045`) — đây là lệch
TargetFramework, **không phải lỗi code**. Trước khi demo phải chốt: cài SDK 10 hoặc hạ
`TargetFramework` của project test.

---

## Phần 4 — Kiểm thử hiệu năng & Demo trực quan (2.5đ) — SV3 🔴

### 4a. Dữ liệu mẫu — 1.0đ 🟢

| Yêu cầu đề bài | Bằng chứng | Trạng thái |
|---|---|---|
| MongoDB ≥ 100 bài viết có tiêu đề, nội dung, **hình ảnh** | `scripts/SeedPosts/seed.py` — `DEFAULT_POST_COUNT = 100`, chặn `--count < 100` ngay từ tham số | 🟢 Script có |
| | `scripts/SeedPosts/import_real.py`, `import_rss.py`, `categorize_real.py`, `verify_real.py` — commit `21a1cd4` (SCRUM-32) | |
| Redis 20–50 session/cache key **TTL khác nhau** | `scripts/SeedRedis/seed_redis.py` — TTL session rải đều 300→1800s, cache ≤600s, có Lua script và bộ verify — commit `6088fe2` (SCRUM-36) | 🟢 Script có |

- [ ] **CẦN XÁC NHẬN:** script có rồi, nhưng **đã chạy thật vào DB dùng để demo chưa?**
      Ngày 30/09 DB còn 6 bài test tay. Trước demo phải `db.posts.drop()`,
      `db.users.drop()` rồi seed lại sạch.

### 4b. Demo trực quan & đo hiệu năng — 1.5đ 🔴

| Bước kịch bản demo (đề bài) | Hạ tầng đã có | Thiếu |
|---|---|---|
| **B1.** SV3 mở Network (F12): lần 1 đọc MongoDB ~200ms vs lần 2 đọc Redis <5ms | Header `X-Cache` + badge HIT/MISS + hiển thị response time — `src/frontend/src/components/CacheStatusBadge.jsx`, commit `b95673c` (SCRUM-38) | **Không có số đo nào được ghi lại, không có biểu đồ** |
| **B2.** SV1 sửa bài → SV2 chứng minh cache cũ bị xóa | `PostsController.Update` ghi Mongo trước, xóa `post:{id}` + `INCR posts:ver` sau | 🟢 Đủ |
| **B3.** SV3 mở RedisInsight chỉ key session đếm lùi TTL | RedisInsight cổng 5540 trong `docker-compose.yml` | 🟢 Đủ |

**Lỗ hổng lớn nhất của cả nhóm:**

- [ ] 🔴 **`scripts/Benchmark/benchmark.py` vẫn là khung rỗng** — 33 dòng, nội dung là
      `# TODO [SV3]: Implement benchmark script` và một dòng `print("TODO: ...")`.
      File này chỉ xuất hiện ở commit dựng khung `86eaff6` (20/08) và **chưa ai chạm
      vào từ đó đến nay**.
- [ ] 🔴 **SCRUM-40** (benchmark Apache Bench / k6) · **SCRUM-41** (biểu đồ so sánh thời
      gian tải) · **SCRUM-42** (chương kiểm thử hiệu năng) — soi toàn bộ `git log --all`
      **không có commit nào** mang các mã này.
- [ ] **SCRUM-43/44/45** (kiểm thử hồi quy, slide, tổng duyệt demo) — cũng không có commit.

> Bộ test Vitest của SV3 (`*.test.jsx`, 9 file) là **test chức năng giao diện**, không
> phải đo hiệu năng — không thay được SCRUM-40/41/42.
>
> **Việc tối thiểu để cứu mục này:** chạy `GET /api/posts/slug/{slug}` (không cache) và
> `GET /api/posts/{id}` (có cache) mỗi bên 20 lần, ghi lại ms, vẽ một biểu đồ cột.
> Ước 2 giờ làm. Không cần Apache Bench hay k6 mới có số để báo cáo.

---

## Việc tồn đọng ngoài barem (không mất điểm trực tiếp, nhưng dễ lộ khi chấm)

- [ ] `src/NewsCacheSession.Api/CLAUDE.md` còn mục "Việc còn thiếu của SV2" liệt kê 6 việc
      **SV2 đã làm xong hết** → sửa (SV1, mục 3 kế hoạch 23/10)
- [ ] `docs/nosql-jira-tasks.csv` ghi SCRUM-27/29/30/31/32/36/38 là `Idea` dù đã có commit;
      dòng SCRUM-13 lỗi quote CSV → sửa (SV1)
- [ ] `docs/quy_che_repo.md` mô tả nhánh `dev` nhóm không dùng + bảng phân công sai;
      `docs/qua_trinh_dung_khung.md` bảng phân công lỗi thời
- [ ] `docs/TÌM HIỂU VỀ GIT 048_068.pdf` (368K) không liên quan đề tài 06
- [ ] Hai MongoDB cùng chiếm cổng 27017 trên máy SV1 (service native Windows + container
      `news-mongo`) → SCRUM-47
- [ ] Nhánh `chore/claude-md` (commit `1e48c67`) chưa push, chưa merge
- [ ] `docs/SRS_NewsCacheSession_DeTai06_rutgon.md` đang untracked — đã chốt **không**
      dùng làm thước đo chấm; quyết định commit (kèm cảnh báo "không phải hợp đồng dữ
      liệu") hay bỏ

---

## Thứ tự ưu tiên tới hạn 26/10

| Ngày | Việc | Ai | Điểm cứu được |
|---|---|---|---|
| **23/10** | SCRUM-46 checklist này · SCRUM-47 cổng 27017 + chạy README từ đầu · sửa `CLAUDE.md` backend + CSV · tag bản chạy ổn | SV1 | — |
| **23–24/10** | 🔴 **Benchmark + biểu đồ + chương kiểm thử hiệu năng** | **SV3** | **1.0–1.5đ** |
| **24/10** | 🔴 **Chương thiết kế Redis: sơ đồ + ảnh RedisInsight (SCRUM-33)** | **SV1** | **1.5đ** |
| 24/10 | Seed lại DB sạch (≥100 bài) trên máy dùng để demo | SV3 | bảo vệ 1.0đ |
| 24–25/10 | Tính năng mới, mỗi cái một nhánh, **bắt buộc có số đo trước/sau** | cả nhóm | cộng điểm |
| **Trưa 25/10** | ⛔ **Chốt không thêm tính năng mới** | cả nhóm | — |
| 25/10 | Chạy thử trọn kịch bản demo 3 bước trên máy sạch · quay video dự phòng | cả nhóm | 1.5đ |
| 25–26/10 | Slide · chuẩn bị phản biện · SCRUM-48 đóng gói nộp | cả nhóm | — |
