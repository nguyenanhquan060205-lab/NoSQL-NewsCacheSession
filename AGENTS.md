# Hướng dẫn cho AI coding assistant — NoSQL-NewsCacheSession

Đồ án môn NoSQL, Đề tài 06: *Phân hệ caching bài viết và quản lý phiên*.
Redis là HQTCSDL chính, MongoDB là DB gốc. Nhóm 3 người, mỗi người sở hữu file riêng.

**Đọc file này trước khi sửa bất kỳ dòng code nào.** Ba mục đầu là bắt buộc, sai là
vỡ dữ liệu hoặc vỡ kịch bản demo. Chi tiết thiết kế: `docs/mongodb-schema.md`,
`docs/redis-keyspace.md`, `docs/chot-thiet-ke-sv1.md`. Nguyên văn đề bài:
`docs/ĐỀ TÀI 06.docx`.

---

## 1. ⛔ Tên field trong MongoDB là camelCase — không được đổi

`title`, `slug`, `content`, `imageUrl`, `categoryId`, `authorId`, `views`,
`isDeleted`, `deletedAt`, `createdAt`, `updatedAt`, `passwordHash`, `role`, `name`,
`description`.

Model C# ép tên này bằng `[BsonElement("...")]` trên **từng** property
(`Models/Post.cs`, `Models/User.cs`, `Models/Category.cs`). Driver MongoDB mặc định
lấy tên property (PascalCase: `Title`, `CreatedAt`), nên **thêm property mới mà quên
`[BsonElement]` là tạo ra field lệch quy ước**.

Khi ghi dữ liệu từ ngoài (script Python, mongosh, Compass) phải dùng đúng các tên
trên. Ghi sai tên thì API deserialize ra giá trị rỗng: bài viết không có tiêu đề,
`createdAt = 01/01/0001`, trang chủ trắng và sort sai.

`categoryId` và `authorId` lưu **dạng ObjectId**, không phải string — trong Python
phải bọc `ObjectId(...)`. Ghi string thường thì API lọc theo chuyên mục không match
bài nào.

## 2. ⛔ Keyspace Redis — dùng đúng các pattern này

| Key | Kiểu | TTL |
|---|---|---|
| `session:{sessionId}` | Hash | 30 phút, sliding |
| `post:{postId}` | String (JSON) | 10 phút |
| `post:{postId}:views` | String (số) | không TTL |
| `posts:cat:{categoryId}:p{n}` | String (JSON list) | 3 phút |
| `lock:post:{postId}` | String | 5 giây (`SET NX PX 5000`) |

Trong C# **không ghép chuỗi key bằng tay**. Dùng helper có sẵn ở đầu
`Controllers/PostsController.cs`: `CacheKey(id)`, `ViewsKey(id)`, `CachePrefix`,
`ListCachePrefix`. Session key do `Services/RedisSessionService.cs` tự dựng.

Đổi key thì phải sửa đồng thời: helper trong code **và** bảng trong
`docs/redis-keyspace.md`. Thầy chấm 1.5đ bằng cách đối chiếu doc với RedisInsight.

## 3. ⛔ Cache-Aside nằm ở `GET /api/posts/{id}`

Không phải `/api/posts/slug/{slug}`. Endpoint theo slug là endpoint phụ, **cố ý
không cache**. Frontend trang chi tiết phải gọi theo `{id}`, nếu không thì kịch bản
demo "tải lần 1 ~200ms từ Mongo vs lần 2 <5ms từ Redis" không chạy được.

Thứ tự bắt buộc khi sửa/xóa bài: **ghi MongoDB trước, xóa key Redis sau**. Xóa cache
trước rồi mới ghi DB thì một request đọc chen vào giữa sẽ nạp lại đúng dữ liệu cũ và
giữ nó thêm trọn một vòng TTL.

---

## 4. Phân công — chỉ sửa file của mình

| | Thành viên | Vai trò |
|---|---|---|
| SV1 | Hồ Ngọc Phương Như | Data Architect & CRUD Lead |
| SV2 | Nguyễn Anh Quan | Advanced Query Specialist |
| SV3 | Nguyễn Xuân Định | Fullstack Integrator & DB Tester |

Nhóm chia việc theo ticket Jira (`docs/nosql-jira-tasks.csv`). **Không sửa file của
người khác.** Nếu thấy file của người khác cần sửa thì báo cho chủ sở hữu, đừng tự
sửa — sẽ gây conflict và sai phân công.

### SV1 — Hồ Ngọc Phương Như (Data Architect & CRUD Lead)
Thiết kế DB gốc + mô hình dữ liệu Redis; API CRUD bài viết.

```
Models/Post.cs, Models/User.cs, Models/Category.cs
Controllers/AuthController.cs
Controllers/PostsController.cs   (TRỪ GetById và IncrementView — của SV2)
Controllers/CategoriesController.cs
DTOs/Auth/*, DTOs/Posts/*, DTOs/Categories/*
Data/MongoIndexInitializer.cs
docs/mongodb-schema.md, docs/redis-keyspace.md, docs/chot-thiet-ke-sv1.md
```

### SV2 — Nguyễn Anh Quan (Advanced Query Specialist)
Middleware Cache-Aside, TTL/EXPIRE, Cache Invalidation, bộ đếm INCR.

```
Services/ICacheService.cs, Services/RedisCacheService.cs
Services/ISessionService.cs, Services/RedisSessionService.cs
Middleware/SessionAuthMiddleware.cs
Controllers/PostsController.cs → CHỈ 2 method GetById và IncrementView
```

### SV3 — Nguyễn Xuân Định (Fullstack Integrator & DB Tester)
Nạp 100 bài viết, đo hiệu năng, làm web tin tức, điều phối demo.

```
src/frontend/**
scripts/SeedPosts/seed.py
scripts/Benchmark/benchmark.py
```

### File dùng chung — phải hỏi cả nhóm trước khi sửa
```
Program.cs, appsettings.json, Data/MongoContext.cs
docker-compose.yml, README.md, .gitignore
```

## 5. Việc còn thiếu (đang chờ ai làm)

| Việc | Ai | Ghi chú |
|---|---|---|
| `ICacheService.RemoveByPrefixAsync(prefix)` | SV2 | Thiếu thì `Create`/`Update`/`Delete` không xóa được cache danh sách `posts:cat:*` → đăng bài mới xong trang chủ đứng im 3 phút |
| Session hash thêm `role`, `lastActive` | SV2 | `Models/User.cs` đã có `Role`; trang admin (SCRUM-29) và trang quản lý phiên (SCRUM-31) cần |
| `GetById` ghi đè `PostResponse.Views` bằng `GET post:{id}:views` | SV2 | Không làm thì UI hiện views đứng im trong khi RedisInsight nhảy số |
| TTL session vào `appsettings.json` | SV2 | Đang hardcode 30 phút ở `AuthController.SessionTtl`; middleware hardcode lần nữa là lệch |
| `builder.Services.AddHostedService<MongoIndexInitializer>();` trong `Program.cs` | SV2 | Thiếu dòng này thì index Mongo không được tạo |
| Seed collection `categories` | SV3 | API tạo/sửa bài kiểm tra `categoryId` tồn tại thật, không có chuyên mục thì trả 400 |
| `api.js` truyền `categoryId` vào `GET /api/posts` | SV3 | SCRUM-18 đã hỗ trợ lọc nhưng frontend chưa gọi |

## 6. Quy ước làm việc

- **Branch**: `SCRUM-<số>-<mô-tả-ngắn>`, tách từ `main`. Merge qua Pull Request.
- **Commit**: `feat(SCRUM-16): API tạo và sửa bài viết` — tiếng Việt, có mã ticket.
- **Không thêm dòng `Co-Authored-By: Claude`** vào commit hay PR.
- **Comment và message lỗi viết tiếng Việt**, giống code hiện có.
- Trước khi sửa: `git fetch --all` rồi kiểm tra branch người khác, tránh đổi thiết kế
  khi người khác đã build lên trên nền cũ.

## 7. Chạy dự án

```bash
docker compose up -d                                  # MongoDB + Redis + RedisInsight
dotnet run --project src/NewsCacheSession.Api         # API, Swagger ở /swagger
cd src/frontend && npm install && npm run dev         # frontend Vite
```

`GET /health` trả JSON tình trạng MongoDB và Redis.
Mongo: `mongodb://localhost:27017`, database `newsdb`. Redis: `localhost:6379`.

> ⚠️ Dữ liệu test cũ (ghi trước 30/09/2026) dùng tên field PascalCase nên **không
> đọc được nữa**. Cần `db.posts.drop()`, `db.users.drop()` rồi seed lại.

## 8. Barem chấm điểm — để biết việc gì thực sự quan trọng

| Phần | Điểm |
|---|---|
| Báo cáo & thiết kế CSDL (nguyên lý Cache-Aside 1.0đ + mô hình Hashes/Strings/khóa 1.5đ) | 2.5 |
| CRUD nền tảng (đăng ký/đăng nhập, viết/sửa/xóa bài) | 2.5 |
| Cache-Aside + Session Hashes + INCR lượt xem | 2.5 |
| Dummy data (≥100 bài viết có ảnh, 20–50 key Redis với TTL khác nhau) + demo sống | 2.5 |

Kịch bản demo: (1) mở tab Network F12, tải bài viết lần 1 vs lần 2; (2) sửa bài viết
→ chứng minh cache cũ bị xóa ngay; (3) mở RedisInsight chỉ ra key session đếm lùi TTL.
