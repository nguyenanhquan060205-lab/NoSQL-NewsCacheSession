# Hướng dẫn cho AI coding assistant — NoSQL-NewsCacheSession

Đồ án môn NoSQL, Đề tài 06: *Phân hệ caching bài viết và quản lý phiên*.
Redis là HQTCSDL chính, MongoDB là DB gốc. Nhóm 3 người, mỗi người sở hữu file riêng.

**Đọc file này trước khi sửa bất kỳ dòng code nào.** Ba mục đầu là bắt buộc, sai là
vỡ dữ liệu hoặc vỡ kịch bản demo. Chi tiết thiết kế: `docs/mongodb-schema.md`,
`docs/redis-keyspace.md`, `docs/chot-thiet-ke-sv1.md`. Nguyên văn đề bài:
`docs/ĐỀ TÀI 06.docx`.

---

## 0. ⛔ Quy tắc bắt buộc trước khi bắt đầu bất kỳ tác vụ nào (Pre-flight Checklist)

Mỗi khi AI hoặc thành viên bắt đầu làm một task/tính năng mới, **bắt buộc phải thực hiện đủ 4 bước kiểm tra sau**:

1. **Kiểm tra phân công file (Mục 4)**: Xác định rõ file cần sửa thuộc quyền của ai (SV1, SV2 hay SV3). Tuyệt đối **không sửa file của người khác**, nếu cần thay đổi hãy báo chủ sở hữu file.
2. **Kích hoạt & Đọc Skill dự án**: Đọc và tuân thủ chặt chẽ skill [`.agents/skills/ak-dotnet-backend/SKILL.md`](.agents/skills/ak-dotnet-backend/SKILL.md) cùng các tài liệu tham khảo trong thư mục `references/` (`redis-patterns.md`, `mongodb-guidelines.md`, `session-and-auth.md`).
3. **Đối chiếu 3 nguyên tắc dữ liệu cốt lõi (Mục 1, 2, 3)**:
   - Field MongoDB luôn là `camelCase` với `[BsonElement("...")]` trên từng property; `categoryId` và `authorId` bắt buộc dạng `ObjectId`.
   - Redis Keyspace chuẩn theo bảng ở Mục 2, dùng helper có sẵn, không nối chuỗi thủ công.
   - Luồng Cache-Aside: luôn **ghi MongoDB trước, xóa/vô hiệu hóa Redis sau**.
4. **Kiểm tra Git & Branch (Mục 7)**: Đảm bảo đã kéo code mới nhất từ `main` (`git pull`), làm việc trên đúng branch ticket `SCRUM-<số>-<mô-tả-ngắn>`, commit bằng tiếng Việt và có mã ticket.

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
| `posts:cat:{categoryId}:p{n}:v{ver}` | String (JSON list) | 3 phút |
| `posts:ver` | String (số) | không TTL — `INCR` để vô hiệu hóa cache danh sách |
| `lock:post:{postId}` | String | 5 giây (`SET NX PX 5000`) |

Trong C# **không ghép chuỗi key bằng tay**. Dùng helper có sẵn ở đầu
`Controllers/PostsController.cs`: `CacheKey(id)`, `ViewsKey(id)`, `CachePrefix`,
`ListCachePrefix`, `ListVersionKey`, `BumpListVersionAsync()`.
Session key do `Services/RedisSessionService.cs` và `Services/CurrentUserService.cs` dựng.

Field trong Hash `session:{sessionId}`: `userId`, `username`, `loginAt` (SV2 ghi khi
tạo phiên) + `role`, `lastActive` (SV1 ghi qua `CurrentUserService.TouchAsync`).
`role` nằm sẵn trong session nên kiểm tra quyền **không tốn query MongoDB**.

**Cache danh sách dùng số phiên bản, không SCAN+DEL.** Key là
`posts:cat:{categoryId}:p{page}:v{ver}` với `ver` đọc từ `posts:ver`.
Create/Update/Delete đã `INCR posts:ver` sẵn — một lệnh O(1) làm mọi key cũ không
còn ai tra tới, thay vì phải SCAN tìm rồi DEL từng key.

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
Services/ICurrentUserService.cs, Services/CurrentUserService.cs
Services/ISessionQueryService.cs, Services/RedisSessionQueryService.cs
Utils/SlugHelper.cs
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

`ISessionService` (SV2) lo **vòng đời** một phiên; `ISessionQueryService` (SV1) chỉ
**liệt kê** phiên cho trang quản trị. Tách theo hướng CQRS nên không đụng cùng file.
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

## 5. Xác thực & phân quyền

Controller **không tự đọc cookie/session** — dùng `ICurrentUserService.GetAsync(HttpContext)`,
trả `CurrentUser(SessionId, UserId, Username, Role, LoginAt)` với `IsAdmin` sẵn, hoặc
null nếu chưa đăng nhập.

**Tài khoản đăng ký đầu tiên tự động là admin** (bootstrap admin) — không có tài khoản
admin cài sẵn, không để lộ mật khẩu admin trong file cấu hình.

Quyền admin dùng ở: `GET`/`DELETE /api/auth/sessions`, `POST /api/categories`, và
sửa/xóa bài viết của người khác. 100 bài seed có `authorId = null` nên **chỉ admin
sửa/xóa được**.

**Hợp đồng cho `SessionAuthMiddleware` (SV2):** `CurrentUserService` có đường tắt đọc
`HttpContext.Items` để khỏi `HGETALL` lần hai trong cùng request. Middleware phải gán
**đủ bộ**, thiếu `Role` là đường tắt bị bỏ qua:

```csharp
context.Items["UserId"]   = session["userId"];
context.Items["Username"] = session["username"];
context.Items["Role"]     = session["role"];     // BẮT BUỘC
context.Items["LoginAt"]  = session["loginAt"];  // tuỳ chọn
```

## 6. Việc còn thiếu (đang chờ ai làm)

| Việc | Ai | Ghi chú |
|---|---|---|
| `SessionAuthMiddleware` (đang là stub) | SV2 | Gán đủ bộ `HttpContext.Items` như hợp đồng trên + refresh TTL sliding |
| `GetById` — luồng Cache-Aside + lock chống stampede | SV2 | Nhớ ghi đè `PostResponse.Views` bằng `post:{id}:views` nếu key tồn tại |
| `IncrementView` — `INCR post:{id}:views` + job flush về `posts.views` | SV2 | |
| Cache danh sách trang chủ (SCRUM-26) | SV2 | Đọc `posts:ver` rồi ghép vào key; **không** cần thêm method vào `ICacheService` |
| Header `X-Cache: HIT\|MISS` trong `GetById` | SV2 | SCRUM-38 của SV3 cần để hiện badge — chốt tên header rồi nói cho SV3 |
| TTL session vào `appsettings.json` (`SessionSettings:TtlMinutes`) | SV2 | Đang hardcode 30 phút ở `AuthController.SessionTtl` |
| Seed collection `categories` | SV3 | API tạo/sửa bài kiểm tra `categoryId` tồn tại thật, không có chuyên mục thì trả 400 |
| `api.js` truyền `categoryId` vào `GET /api/posts` | SV3 | SCRUM-18 đã hỗ trợ lọc nhưng frontend chưa gọi |
| Upload ảnh bài viết (SCRUM-39) | SV3 | Chưa chốt: dùng URL ngoài (picsum) hay cần endpoint upload file ở backend |

## 7. Quy ước làm việc

- **Branch**: `SCRUM-<số>-<mô-tả-ngắn>`, tách từ `main`. Merge qua Pull Request.
- **Commit**: `feat(SCRUM-16): API tạo và sửa bài viết` — tiếng Việt, có mã ticket.
- **Không thêm dòng `Co-Authored-By: Claude`** vào commit hay PR.
- **Comment và message lỗi viết tiếng Việt**, giống code hiện có.
- Trước khi sửa: `git fetch --all` rồi kiểm tra branch người khác, tránh đổi thiết kế
  khi người khác đã build lên trên nền cũ.

## 8. Chạy dự án

```bash
docker compose up -d                                  # MongoDB + Redis + RedisInsight
dotnet run --project src/NewsCacheSession.Api         # API, Swagger ở /swagger
cd src/frontend && npm install && npm run dev         # frontend Vite
```

`GET /health` trả JSON tình trạng MongoDB và Redis.
Mongo: `mongodb://localhost:27017`, database `newsdb`. Redis: `localhost:6379`.

> ⚠️ Dữ liệu test cũ (ghi trước 30/09/2026) dùng tên field PascalCase nên **không
> đọc được nữa**. Cần `db.posts.drop()`, `db.users.drop()` rồi seed lại.

## 9. Barem chấm điểm — để biết việc gì thực sự quan trọng

| Phần | Điểm |
|---|---|
| Báo cáo & thiết kế CSDL (nguyên lý Cache-Aside 1.0đ + mô hình Hashes/Strings/khóa 1.5đ) | 2.5 |
| CRUD nền tảng (đăng ký/đăng nhập, viết/sửa/xóa bài) | 2.5 |
| Cache-Aside + Session Hashes + INCR lượt xem | 2.5 |
| Dummy data (≥100 bài viết có ảnh, 20–50 key Redis với TTL khác nhau) + demo sống | 2.5 |

Kịch bản demo: (1) mở tab Network F12, tải bài viết lần 1 vs lần 2; (2) sửa bài viết
→ chứng minh cache cũ bị xóa ngay; (3) mở RedisInsight chỉ ra key session đếm lùi TTL.
