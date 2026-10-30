# Phân công, cách thực hành và kịch bản demo — Đề tài 06

**Lập ngày 23/10/2026.** Tổng hợp từ đề bài gốc `docs/ĐỀ TÀI 06.docx`, `AGENTS.md`,
`docs/nosql-jira-tasks.csv`, lịch sử git và **một lượt chạy thật toàn bộ kịch bản** trên
API đang chạy (kết quả ở mục 8). Mọi lệnh trong file đều đã chạy thử.

> **Đọc theo thứ tự:** mục 1–2 để nắm đề, mục 3–5 là phần việc của từng người, mục 6–7
> là kịch bản đứng trước thầy, mục 8–10 là kết quả kiểm thử, lỗi và việc phải làm trước demo.

---

## 1. Đề bài yêu cầu gì

**Sản phẩm:** trang tin tức có đăng nhập, đọc bài; tích hợp bộ nhớ đệm để tăng tốc tải trang.
**Redis là HQTCSDL chính**, MongoDB là DB gốc.

| Phần barem | Điểm | Ai chịu trách nhiệm chính |
|---|---|---|
| 1. Báo cáo & thiết kế CSDL — nguyên lý Cache-Aside (1.0) + mô hình Hashes/Strings/khóa (1.5) | 2.5 | SV2 (1.0) · SV1 (1.5) |
| 2. CRUD nền tảng — đăng ký/đăng nhập, viết/sửa/xóa bài trên DB gốc | 2.5 | SV1 |
| 3. Nâng cao — Cache-Aside + TTL + Cache Invalidation; Session bằng Hash; INCR lượt xem | 2.5 | SV2 |
| 4. Dummy data (1.0) + demo sống (1.5) | 2.5 | SV3 (cả nhóm cùng diễn) |

**Định mức dữ liệu:** MongoDB ≥ 100 bài có tiêu đề, nội dung, hình ảnh · Redis 20–50
key session/cache có **TTL khác nhau**.

**Ba bước demo bắt buộc (nguyên văn đề):**
1. SV3 mở tab Network (F12) tải bài viết lần 1 (đọc DB gốc ~200ms) vs lần 2 (đọc Redis <5ms).
2. SV1 sửa nội dung bài viết → SV2 chứng minh Cache cũ bị xóa ngay lập tức.
3. SV3 mở RedisInsight chỉ ra key Session tự động đếm lùi TTL.

---

## 2. Hệ thống chạy thế nào (một hình)

```
Trình duyệt (React, :3000) ──proxy /api──► ASP.NET Core API (:5134)
                                              │
              ┌───────────────────────────────┼──────────────────────────────┐
              ▼                               ▼                              ▼
   SessionAuthMiddleware            PostsController.GetById        PostsController.Update/Delete
   HGETALL session:{sid}            1. GET post:{id}  ──HIT──► trả   1. ghi MongoDB TRƯỚC
   EXPIRE 1800 (sliding)            2. MISS → SET lock NX EX 5       2. DEL post:{id}
                                    3. đọc MongoDB                   3. INCR posts:ver
                                    4. SETEX post:{id} 600 {json}
                                    5. nhả lock (Lua)
              │                               │
              ▼                               ▼
        Redis (:6379)  ◄────── ViewCountSyncWorker (1 phút/lần) ──────►  MongoDB (newsdb)
        session:*  post:*  post:*:views  posts:cat:*  posts:ver           posts · users · categories
```

| Key Redis | Kiểu | TTL | Ai ghi |
|---|---|---|---|
| `session:{sessionId}` | Hash (`userId, username, role, loginAt, lastActive`) | 1800s, sliding | SV2 tạo/gia hạn, SV1 ghi `role` |
| `post:{postId}` | String JSON | 600s | SV2 (`GetById`) |
| `post:{postId}:views` | String số | không TTL | SV2 (`IncrementView`) |
| `posts:cat:{cat}:p{n}:v{ver}` | String JSON | 180s | SV2 (`GetAll`, SCRUM-26) |
| `posts:ver` | String số | không TTL | `INCR` khi tạo/sửa/xóa bài |
| `lock:post:{postId}` | String token | 5s | SV2 (chống stampede) |
| `posts:dirty_views` | Set | không TTL | SV2 (worker write-behind) |

---

## 3. SV1 — Hồ Ngọc Phương Như · Data Architect & CRUD Lead

### Đã làm gì

| Việc | File | Ticket |
|---|---|---|
| Thiết kế 3 collection MongoDB, quy ước camelCase bằng `[BsonElement]`, `categoryId`/`authorId` lưu ObjectId | `Models/Post.cs`, `User.cs`, `Category.cs` | SCRUM-33 |
| Tài liệu thiết kế + hợp đồng dữ liệu cho nhóm | `docs/mongodb-schema.md`, `docs/redis-keyspace.md`, `docs/chot-thiet-ke-sv1.md` | SCRUM-33 |
| Đăng ký (BCrypt), đăng nhập (tạo session Redis + cookie HttpOnly), đăng xuất, `/me` | `Controllers/AuthController.cs` | SCRUM-13 |
| Tài khoản đăng ký **đầu tiên tự là admin** | `AuthController.Register` | SCRUM-13 |
| Tạo / sửa / xóa mềm bài viết, slug tiếng Việt không trùng, phân quyền admin/tác giả | `Controllers/PostsController.cs` (trừ `GetById`, `IncrementView`), `Utils/SlugHelper.cs` | SCRUM-16/17/29 |
| Danh sách có phân trang + lọc chuyên mục; đọc theo slug (cố ý **không** cache) | `PostsController.GetAll`, `GetBySlug` | SCRUM-18/19 |
| Chuyên mục (đọc công khai, tạo chỉ admin) | `Controllers/CategoriesController.cs` | SCRUM-18 |
| Lấy người dùng hiện tại từ Hash session (không tốn query MongoDB) | `Services/CurrentUserService.cs` | — |
| Liệt kê phiên cho admin bằng `SCAN` (không dùng `KEYS`), thu hồi phiên | `Services/RedisSessionQueryService.cs` | SCRUM-31 |
| Tự tạo index lúc khởi động (`ux_posts_slug`, `ix_posts_category_createdAt`...) | `Data/MongoIndexInitializer.cs` | — |

### Dùng gì

- **MongoDB.Driver 3.11**: `Find`, `FindOneAndUpdate`, `UpdateOne`, filter `Ne(isDeleted, true)`, unique index.
- **BCrypt.Net**: hash mật khẩu (`$2a$11$...` — đã kiểm tra trong DB).
- **Redis**: `HSET` field `role`, `lastActive` vào Hash session; `SCAN session:*` để liệt kê phiên.
- **Swagger** (`/swagger`) để thao tác CRUD khi demo.

### Thực hành / demo phần của SV1

1. **Mở Swagger** `http://localhost:5134/swagger` → `POST /api/auth/register` → chỉ ra người
   đầu tiên nhận `role: "admin"`, người sau nhận `role: "user"`.
2. `POST /api/auth/login` sai mật khẩu và sai username → **cùng** một câu
   `"Sai username hoặc password"` (không lộ username nào tồn tại).
3. Trên web: đăng nhập admin → **Sửa** một bài → **Lưu** (đây là bước 2 của đề, xem mục 6).
4. Chứng minh phân quyền: đăng nhập tài khoản thường, sửa bài seed → **403** (bài seed không
   có tác giả, chỉ admin sửa được — thiết kế có chủ ý).
5. Trình bày thiết kế: mở RedisInsight chỉ từng loại key ở bảng mục 2 — thầy chấm 1.5đ bằng
   cách **đối chiếu tài liệu với RedisInsight**.

Câu hỏi phản biện và câu trả lời mẫu: nhánh `SCRUM-46-checklist-doi-chieu-barem`, file
`docs/kich-ban-trinh-bay-sv1.md` (16 câu).

---

## 4. SV2 — Nguyễn Anh Quân · Advanced Query Specialist

### Đã làm gì

| Việc | File | Ticket |
|---|---|---|
| Session lưu bằng **Hash** + `EXPIRE` 30 phút | `Services/RedisSessionService.cs` | SCRUM-14 |
| Middleware xác thực + **sliding expiration** (gia hạn TTL + `lastActive` trong một transaction, không tạo lại phiên đã hết hạn) | `Middleware/SessionAuthMiddleware.cs` | SCRUM-15 |
| Wrapper cache + đếm hit/miss, endpoint `/api/cache/stats` | `Services/RedisCacheService.cs`, `Controllers/CacheStatsController.cs` | SCRUM-20/34 |
| **Cache-Aside** ở `GET /api/posts/{id}` + header `X-Cache: HIT/MISS` | `PostsController.GetById` | SCRUM-21/38 |
| **Khóa chống cache stampede** (`SET lock NX` + TTL 5s, nhả khóa bằng Lua kiểm token) | `GetById`, `RedisCacheService.AcquireLockAsync/ReleaseLockAsync` | SCRUM-24 |
| **Cache Invalidation** khi sửa/xóa: ghi MongoDB trước, xóa Redis sau | `PostsController.Update/Delete` | SCRUM-23 |
| Cache danh sách trang chủ bằng **số phiên bản** `posts:ver` (vô hiệu hóa O(1), không SCAN+DEL) | `PostsController.GetAll` | SCRUM-26 |
| **Bộ đếm lượt xem `INCR`** + worker **write-behind** đồng bộ về MongoDB mỗi phút (`SPOP` nguyên tử) | `PostsController.IncrementView`, `Services/ViewCountSyncWorker.cs` | SCRUM-25 |
| Test tự động (xUnit + Moq + FluentAssertions), 27 test | `tests/NewsCacheSession.Tests/` | SCRUM-35/37 |
| Báo cáo nguyên lý Cache-Aside | `docs/bao-cao-nguyen-ly-cache-aside.md` | SCRUM-28 |

### Dùng gì — các lệnh Redis thật sự chạy

Bắt được bằng `redis-cli MONITOR` trong lúc đọc → sửa → đọc lại một bài:

```
GET     post:{id}                                 ← tra cache (HIT thì dừng ở đây)
GET     post:{id}:views                           ← lượt xem realtime ghi đè vào kết quả
HGETALL session:{sid}                             ← middleware đọc phiên
MULTI / HSET lastActive / EXPIRE 1800 / EXEC      ← sliding expiration
UNLINK  post:{id}                                 ← ⭐ sửa bài: xóa cache (DEL không chặn)
INCR    posts:ver                                 ← ⭐ vô hiệu hóa toàn bộ cache danh sách
GET     post:{id}                                 ← đọc lại: MISS
SET     lock:post:{id} <token> EX 5 NX            ← giành khóa chống stampede
SETEX   post:{id} 600 {json}                      ← ⭐ ghi ngược Redis kèm TTL
WATCH / GET lock / MULTI / UNLINK lock / EXEC     ← nhả khóa đúng token
```

> Lưu ý khi trả lời thầy: tài liệu ghi `SET NX PX 5000`, còn thư viện gửi `SET ... EX 5 NX`
> — **cùng ý nghĩa** (5 giây = 5000 ms). Xóa key, thư viện dùng `UNLINK` (bản không chặn của `DEL`).

### Thực hành / demo phần của SV2

1. **Bước 2 của đề** (mục 6): sau khi SV1 bấm Lưu, mở RedisInsight → key `post:{id}` biến mất,
   `posts:ver` tăng 1.
2. **Bằng chứng mạnh hơn (tuỳ chọn):** mở sẵn một cửa sổ lệnh chạy
   `docker exec -it news-redis redis-cli MONITOR` — khi SV1 bấm Lưu, dòng `UNLINK post:{id}`
   và `INCR posts:ver` hiện ra **ngay lập tức**. Tắt bằng `Ctrl+C` sau khi demo
   (MONITOR làm chậm Redis, không để chạy lâu).
3. **INCR lượt xem**: mở một bài, bấm `Ctrl+R` vài lần → RedisInsight thấy
   `post:{id}:views` tăng; key này **không có TTL** (TTL = -1). Chờ ~1 phút → MongoDB
   `posts.views` khớp con số đó (write-behind).
4. **Thống kê**: `GET /api/cache/stats` → `hits`, `misses`, `hitRate`.
5. **Chạy test**: `dotnet test` → 27/27 qua (cần .NET SDK 10 — xem mục 10).

---

## 5. SV3 — Nguyễn Xuân Định · Fullstack Integrator & DB Tester

### Đã làm gì

| Việc | File | Ticket |
|---|---|---|
| Web tin tức React + Vite + Tailwind: trang chủ, chi tiết, đăng nhập/đăng ký, admin CRUD bài, admin quản lý phiên | `src/frontend/src/pages/*`, `components/*` | SCRUM-22/27/29/30/31 |
| **Badge `CACHE HIT/MISS` + thời gian phản hồi** đo tại trình duyệt (đọc header `X-Cache`) | `components/CacheStatusBadge.jsx`, `services/api.js` | SCRUM-38 |
| Trang chi tiết gọi đúng `GET /api/posts/{id}` (có cache) rồi `POST /view` (INCR) | `pages/PostDetailPage.jsx` | SCRUM-27 |
| Seed **100 bài có ảnh** + 5 chuyên mục, chạy lại an toàn (upsert theo slug), chặn `--count < 100` | `scripts/SeedPosts/seed.py` | SCRUM-32 |
| Nhập tin thật VnExpress / RSS (tuỳ chọn, có ảnh + nguồn) | `scripts/SeedPosts/import_real.py`, `import_rss.py`, `categorize_real.py` | SCRUM-32 |
| Seed **40 hoặc 50 key Redis**: 20–25 session Hash TTL rải 300→1800s + 20–25 cache bài thật TTL 600s, có manifest/resume | `scripts/SeedRedis/seed_redis.py` | SCRUM-36 |
| Test giao diện Vitest: 11 file, 101 test | `src/frontend/src/**/*.test.jsx` | — |

### Dùng gì

React 19 + React Router, axios (proxy `/api` → `:5134`), Tailwind 4, Vitest + Testing Library,
Python (`pymongo`, `Faker`, `redis`), RedisInsight (`:5540`), DevTools tab Network.

### Thực hành / demo phần của SV3

1. **Chuẩn bị dữ liệu** (trước buổi demo):
   ```bash
   python scripts/SeedPosts/seed.py                       # 100 bài có ảnh
   # đăng ký một tài khoản THƯỜNG trên web (vd: demo_user) rồi:
   python scripts/SeedRedis/seed_redis.py --demo-username demo_user --total 40
   docker exec news-redis redis-cli DBSIZE               # phải ≥ 20
   ```
2. **Bước 1 của đề** và **bước 3 của đề**: xem mục 6.
3. **Đo hiệu năng + biểu đồ** (SCRUM-40/41): đo 20 lượt mỗi loại (không cache / MISS / HIT),
   vẽ cột. Số đo thật ở mục 11. `scripts/Benchmark/benchmark.py` **vẫn là khung rỗng** — xem mục 9.
4. **Điều phối demo**: mở sẵn 2 tab (`localhost:3000`, `localhost:5540`), đếm thời gian, chuyển
   lượt nói giữa ba người.

---

## 6. Kịch bản demo chính — 3 bước theo đề

Chuẩn bị: API + frontend + RedisInsight đang chạy, đã seed dữ liệu (mục 10).
Tab 1 `http://localhost:3000`, tab 2 `http://localhost:5540` (RedisInsight → Browser).

### 🎬 Bước 1 — Lần 1 đọc MongoDB, lần 2 đọc Redis · *SV3 (Định)*

| # | Thao tác | Thấy gì |
|---|---|---|
| 1 | Tab 1 → `F12` → thẻ **Network** | Bảng request |
| 2 | Bấm vào một bài **chưa ai mở** | Badge **`CACHE MISS`**; request `GET /api/posts/{id}` có header `X-Cache: MISS` |
| 3 | `Ctrl+R` | Badge **`CACHE HIT`**, số ms **nhỏ hơn**; header `X-Cache: HIT` |
| 4 | (tuỳ chọn) Tab 2 tìm `post:*` | Key `post:{id}` kiểu String, TTL ~600 đang giảm |

**Câu chốt:** *"MISS là đọc MongoDB rồi ghi ngược vào Redis kèm TTL 10 phút; HIT là đọc thẳng Redis."*

### 🎬 Bước 2 — Sửa bài, cache cũ bị xóa ngay · *SV1 sửa, SV2 chứng minh*

| # | Ai | Thao tác | Thấy gì |
|---|---|---|---|
| 1 | SV2 | Tab 2 tìm `post:*`, bấm key của bài đang mở | Key tồn tại, TTL đang giảm |
| 2 | SV1 | Tab 1 đăng nhập **admin** → **Sửa** bài → đổi tiêu đề → **Lưu** | Lưu thành công |
| 3 | SV2 | Tab 2 bấm **làm mới** | Key `post:{id}` **biến mất**; `posts:ver` tăng 1 |
| 4 | SV3 | Tab 1 mở lại bài | Badge **`MISS`**, tiêu đề **mới** |
| 5 | SV3 | `Ctrl+R` | Badge **`HIT`** trở lại |

**Câu chốt:** *"Ghi MongoDB trước, xóa Redis sau — không ai đọc phải bản cũ."*

### 🎬 Bước 3 — Session đếm lùi TTL · *SV3 (Định)*

| # | Thao tác | Thấy gì |
|---|---|---|
| 1 | Tab 1 đăng nhập | — |
| 2 | Tab 2 tìm `session:*`, bấm vào key | Kiểu **Hash**: `userId`, `username`, `role`, `loginAt`, `lastActive` |
| 3 | Bấm làm mới vài lần | **TTL giảm dần** từ 1800 |
| 4 | Tab 1 bấm một bài bất kỳ, quay lại tab 2 làm mới | TTL **nhảy về 1800**, `lastActive` đổi (sliding) |

**Câu chốt:** *"Còn hoạt động thì phiên được gia hạn; bỏ 30 phút thì Redis tự xóa phiên."*

---

## 7. Kịch bản bổ sung — dùng khi còn thời gian hoặc khi thầy hỏi

| Mã | Kịch bản | Ai | Cách làm | Kết quả đúng |
|---|---|---|---|---|
| B1 | **INCR lượt xem realtime** | SV2 | Mở một bài, `Ctrl+R` 5 lần; xem `post:{id}:views` | Tăng đúng 5; TTL = -1 |
| B2 | **Write-behind về MongoDB** | SV2 | Chờ ~1 phút sau B1 | `posts.views` trong MongoDB bằng số trong Redis |
| B3 | **Khóa chống stampede** | SV2 | Xóa `post:{id}`, bắn 40 request cùng lúc | Chỉ **1 MISS**, 39 HIT; không còn sót key `lock:` |
| B4 | **Cache danh sách theo phiên bản** | SV2 | Mở trang chủ 2 lần → tạo/sửa bài → mở lại | Lần 2 HIT; sau khi sửa: key mới `...:v{n+1}`, bài mới đứng đầu |
| B5 | **Xóa mềm + invalidation** | SV1 | Xóa một bài | `post:{id}` mất, `isDeleted=true`, GET trả 404; **giữ** `post:{id}:views` |
| B6 | **Phân quyền** | SV1 | User thường sửa bài seed; chưa đăng nhập sửa bài | 403; 401; cache **không** bị xóa |
| B7 | **Quản trị phiên** | SV1/SV3 | Admin vào trang *Phiên đăng nhập*, thu hồi phiên của user khác | Key `session:*` của user biến mất; user đó bị 401; user thường vào trang này bị 403 |
| B8 | **Đăng xuất** | SV1 | Bấm Đăng xuất | Key `session:{sid}` bị xóa ngay |
| B9 | **Định mức dữ liệu** | SV3 | `countDocuments` + `redis-cli DBSIZE` | ≥ 100 bài có ảnh; 20–50 key, TTL khác nhau |
| B10 | **Số đo hiệu năng** | SV3 | Chiếu biểu đồ 20 lượt (mục 11) | HIT nhanh hơn MISS ~3 lần |
| B11 | **Sức khỏe hệ thống** | bất kỳ | `curl http://localhost:5134/health` | `mongodb` và `redis` đều `Healthy` |

Lệnh cho B9:

```bash
docker exec news-mongo mongosh --quiet --eval "db.getSiblingDB('newsdb').posts.countDocuments({imageUrl:{\$regex:'^https?://'}})"
docker exec news-redis redis-cli DBSIZE
docker exec news-redis redis-cli --scan --pattern 'session:*' | head -5 | xargs -I{} docker exec news-redis redis-cli TTL {}
```

---

## 8. Kết quả chạy thật ngày 23/10/2026

**Môi trường kiểm thử:** macOS, API chạy từ mã nguồn hiện tại trên `main`, MongoDB Docker
(database tách riêng `newsdb_kiemthu`, 100 bài seed bằng `seed.py`), Redis DB số 1 (tách khỏi
dữ liệu demo ở DB 0). Gọi API trực tiếp và qua proxy Vite `:3000`.

| Kịch bản | Kết quả | Bằng chứng |
|---|---|---|
| **Đề 1** — MISS → HIT | ✅ | `X-Cache: MISS` 4.8 ms → `HIT` 1.5 ms; key `post:{id}` String, TTL 600 |
| **Đề 2** — sửa bài → cache bị xóa | ✅ | Ngay sau PUT: `EXISTS post:{id}=0`, `posts:ver` 0→1; GET kế tiếp MISS với tiêu đề mới, lần sau HIT |
| **Đề 3** — session Hash đếm lùi TTL | ✅ | Hash đủ 5 field; TTL 1786→1783→1781 khi đứng yên; 1 request → TTL 1800, `lastActive` đổi |
| B1 INCR | ✅ | 5 lượt → 5; 50 request song song → đúng +50; ID không tồn tại → 404, không tạo key |
| B2 write-behind | ✅ (sau khi sửa lỗi) | Mongo `views` = Redis sau ≤ 60s — xem lỗi #1 mục 9 |
| B3 stampede | ✅ | 40 request đồng thời: 1 MISS + 39 HIT, không sót lock |
| B4 cache danh sách | ✅ | HIT lần 2; đổi `pageSize` → MISS, trả đúng 5 bài; tạo bài → `posts:ver` tăng, bài mới đứng đầu |
| B5 xóa mềm | ✅ | 204; cache mất, `isDeleted=true`, GET 404, key views được giữ |
| B6 phân quyền | ✅ | User thường sửa bài seed 403 (cache giữ nguyên); chưa đăng nhập 401; chuyên mục sai 400; tác giả tự sửa bài mình 200 |
| B7 quản trị phiên | ✅ | User 403; admin thấy 2 phiên; tự thu hồi mình 400; thu hồi user 204 → user 401, không tạo lại Hash mồ côi |
| B8 đăng xuất | ✅ | Key session bị xóa |
| Đăng ký/đăng nhập | ✅ | User đầu = admin; trùng username 409; sai mật khẩu/username cùng thông báo 401; cookie `HttpOnly; SameSite=Lax; Max-Age=1800`; mật khẩu BCrypt |
| Slug tiếng Việt | ✅ | "Bài mới của Đường Đức" → `bai-moi-cua-duong-duc`, trùng → `-2`, `-3` |
| Seed 100 bài | ✅ | 100/100 có ảnh, `categoryId` kiểu ObjectId, 0 field PascalCase; chạy lại không nhân đôi; `--count 50` bị chặn |
| Test .NET | ✅ | 27/27 (26 cũ + 1 test mới cho lỗi #1) |
| Test script seed | ✅ | `test_seed.py` 7/7, `test_seed_redis.py` 33/33 |
| Frontend | ✅ | Vitest 101/101, `oxlint` sạch, `vite build` thành công; proxy `:3000` trả đúng `X-Cache` và cookie |
| Seed 20–50 key Redis trên máy này | ⚠️ **chưa chạy được** | Xem lỗi #4 mục 9 |
| Benchmark của SV3 | ❌ **chưa có** | `scripts/Benchmark/benchmark.py` vẫn là khung TODO |

---

## 9. Lỗi phát hiện

### Đã sửa (phần của SV2, chưa commit)

**#1 — Lượt xem bị reset và ghi đè mất số cũ trong MongoDB.**

- *Hiện tượng (đã tái hiện):* bài có `views = 500` trong MongoDB nhưng Redis chưa có
  `post:{id}:views` → một lượt xem trả `{"views":1}` → sau ≤ 1 phút worker ghi `views = 1`
  đè lên 500 trong MongoDB.
- *Nguyên nhân:* `IncrementView` gọi `INCR` trên key chưa tồn tại nên đếm từ 0, rồi
  `ViewCountSyncWorker` dùng `$set` chép số đó về MongoDB. Xảy ra bất cứ khi nào Redis mất key
  đếm trong khi MongoDB đã có số: `FLUSHALL` (chính `docs/huong_dan_nhom.md` hướng dẫn chạy),
  `docker compose down -v`, demo trên máy có Redis mới nhưng MongoDB cũ.
- *Cách sửa:* ở lượt xem đầu tiên (lúc vốn đã tra MongoDB để chặn ID không tồn tại), đọc luôn
  `posts.views` và khởi tạo bộ đếm bằng `SET NX` (không TTL) trước khi `INCR`. `SET NX` bảo
  đảm nhiều lượt xem đầu tiên chen nhau chỉ khởi tạo một lần.
- *File:* `Controllers/PostsController.cs` (`IncrementView`), `Services/ICacheService.cs`,
  `Services/RedisCacheService.cs` (`SetIfNotExistsAsync`), thêm test ở
  `tests/.../CacheServiceTests.cs` và `ViewCountSyncTests.cs`.
- *Kiểm chứng sau khi sửa:* 500 → 501 → 502; 20 lượt xem đầu tiên song song trên bài có 300 →
  320; sau khi worker chạy, MongoDB giữ đúng 502 và 320.

### Còn tồn — báo chủ sở hữu, chưa sửa

| # | Mức | Vấn đề | Chủ sở hữu | Đề xuất |
|---|---|---|---|---|
| 2 | Trung bình | **Cookie phiên không trượt theo Redis.** Cookie đặt `Max-Age=1800` một lần lúc đăng nhập và không được cấp lại khi gia hạn (đã kiểm: các request sau không có `Set-Cookie`). Dùng liên tục quá 30 phút thì trình duyệt tự xóa cookie, người dùng bị đăng xuất dù Redis vẫn còn phiên. Demo ngắn không lộ, nhưng câu "còn hoạt động thì được gia hạn" chỉ đúng phía Redis. | SV1 (`AuthController.Login`) — hoặc SV2 nếu cấp lại cookie trong middleware | Bỏ `MaxAge` (cookie phiên trình duyệt, để Redis quyết định hạn), hoặc middleware cấp lại cookie mỗi lần gia hạn |
| 3 | Thấp | `AuthController.SessionTtl` hardcode 30 phút, còn middleware đọc `SessionSettings:TtlMinutes`. Đổi cấu hình (vd 2 phút để demo hết hạn nhanh) thì phiên mới vẫn nhận 1800s cho tới request kế tiếp. | SV1 | Đọc cùng một cấu hình |
| 4 | **Cao cho buổi demo** | **Máy Mac này có hai MongoDB:** MongoDB cài bằng Homebrew chiếm `localhost:27017` (rỗng), container `news-mongo` bị map sang `27018` (chứa 100 bài). API chạy mặc định sẽ đọc kho **rỗng**; `seed_redis.py` khóa cứng `localhost:27017` + `newsdb` nên **không seed được 20–50 key**. Redis demo (DB 0) hiện chỉ có **2 key** → chưa đạt định mức. | Cả nhóm (môi trường) | Xem mục 10, bước 1 |
| 5 | Thấp | `POST /api/posts/{id}/view` trên bài **đã xóa mềm** vẫn trả 200 và tiếp tục đếm nếu key đếm còn (chỉ kiểm tra tồn tại ở lượt đầu). Frontend không gọi vì GET đã 404 trước. | SV2 | Chấp nhận được; nếu sửa thì kiểm `post:{id}` hoặc MongoDB mỗi lượt (đánh đổi hiệu năng) |
| 6 | **Cao cho điểm** | `scripts/Benchmark/benchmark.py` vẫn là khung TODO (và trong comment trỏ nhầm cổng `5000`, API thật là `5134`). SCRUM-40/41/42 chưa có commit. | SV3 | Dùng số đo mục 11 hoặc script PowerShell ở `docs/kich-ban-demo-va-do-hieu-nang.md` (nhánh SCRUM-46) |
| 7 | Thấp | JSON trong `post:{id}` lưu tên field PascalCase và tiếng Việt dạng `ô`, khó đọc khi chiếu RedisInsight. Không sai chức năng. | SV2 | Nếu muốn dễ đọc khi demo: dùng `JavaScriptEncoder.UnsafeRelaxedJsonEscaping` khi serialize (giữ nguyên tên field để không vỡ cache đang có) |

---

## 10. Checklist chuẩn bị máy demo

1. **(Máy macOS này)** Gỡ xung đột cổng 27017 rồi tạo lại container theo đúng `docker-compose.yml`
   (volume `mongo_data` giữ nguyên, không mất 100 bài):
   ```bash
   brew services stop mongodb-community
   docker compose up -d --force-recreate mongo
   docker compose ps                     # news-mongo phải là 0.0.0.0:27017->27017
   ```
   Máy Windows: `net stop MongoDB` (xem `docs/kich-ban-demo-va-do-hieu-nang.md` Phần A).
2. `dotnet run --project src/NewsCacheSession.Api --urls http://localhost:5134` → `curl /health` hai lần `Healthy`.
3. Kiểm tra ≥ 100 bài: `curl "http://localhost:5134/api/posts?pageSize=1"` → `totalItems ≥ 100`;
   thiếu thì `python scripts/SeedPosts/seed.py`.
4. Có **tài khoản admin** (người đăng ký đầu tiên; DB demo hiện có `demo_admin`) và **một tài
   khoản thường** cho `seed_redis.py`.
5. `python scripts/SeedRedis/seed_redis.py --demo-username <tài-khoản-thường>` → `redis-cli DBSIZE` ≥ 20.
6. `cd src/frontend && npm run dev` → `http://localhost:3000`.
7. RedisInsight `http://localhost:5540` → thêm DB host `redis` (cùng mạng Docker) hoặc
   `host.docker.internal`, port `6379`.
8. Chọn sẵn một bài **chưa mở** cho Bước 1 (hoặc `redis-cli DEL post:{id}` ngay trước demo).
9. `dotnet test` cần **.NET SDK 10** (project test nhắm `net10.0`); máy chỉ có SDK 9 sẽ báo `NETSDK1045`.

---

## 11. Số đo hiệu năng (20 lượt, đo ngày 23/10/2026)

Máy macOS, MongoDB và Redis cùng chạy Docker trên máy, 100 bài, gọi HTTP qua `localhost`.

| Loại | Trung bình | Trung vị | Nhanh nhất | Chậm nhất |
|---|---|---|---|---|
| Không cache — `GET /api/posts/slug/{slug}` (MongoDB) | 1.80 ms | 1.01 ms | 0.81 ms | 15.90 ms |
| Cache MISS — `GET /api/posts/{id}` sau khi xóa key | 4.36 ms | 3.85 ms | 3.49 ms | 12.27 ms |
| Cache HIT — `GET /api/posts/{id}` lần kế tiếp | 1.38 ms | 1.17 ms | 1.00 ms | 4.52 ms |

**HIT nhanh hơn MISS 3,16 lần.** Kết quả khớp số SV1 đo trên Windows (3,07 lần).

Cách giải thích trung thực khi thầy hỏi vì sao không ra "200 ms vs 5 ms" như đề:
MongoDB chạy ngay trên máy, dữ liệu nhỏ (100 bài nằm gọn trong RAM) và có index nên đọc rất
nhanh. MISS chậm hơn "không cache" vì phải làm thêm: tra Redis, giành khóa, đọc MongoDB, ghi
ngược Redis, nhả khóa. Đó là chi phí bình thường của lần đọc đầu trong Cache-Aside. Muốn chênh
lệch rõ hơn một cách trung thực thì seed nhiều dữ liệu hơn (`seed.py --count 1000`) rồi đo lại.
**Không sửa số.**
