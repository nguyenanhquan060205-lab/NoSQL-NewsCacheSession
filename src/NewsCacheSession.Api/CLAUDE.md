# Backend — ASP.NET Core 8 Web API

MongoDB là DB gốc, Redis là HQTCSDL chính của đề tài. Không dùng ORM nào ngoài
MongoDB.Driver; Redis truy cập qua StackExchange.Redis.

## Phân công trong thư mục này

| File | Chủ sở hữu |
|---|---|
| `Models/*`, `DTOs/*`, `Utils/SlugHelper.cs`, `Data/MongoIndexInitializer.cs` | SV1 — Hồ Ngọc Phương Như |
| `Controllers/AuthController.cs`, `PostsController.cs`, `CategoriesController.cs` | SV1 — Hồ Ngọc Phương Như |
| ↳ **trừ** `PostsController.GetById` và `PostsController.IncrementView` | SV2 — Nguyễn Anh Quan |
| `Services/ICurrentUserService.cs`, `CurrentUserService.cs` | SV1 — Hồ Ngọc Phương Như |
| `Services/ISessionQueryService.cs`, `RedisSessionQueryService.cs` | SV1 — Hồ Ngọc Phương Như |
| `Services/ICacheService.cs`, `RedisCacheService.cs` | SV2 — Nguyễn Anh Quan |
| `Services/ISessionService.cs`, `RedisSessionService.cs` | SV2 — Nguyễn Anh Quan |
| `Middleware/SessionAuthMiddleware.cs` | SV2 — Nguyễn Anh Quan |
| `Program.cs`, `appsettings.json`, `Data/MongoContext.cs` | dùng chung — hỏi cả nhóm |

**Không sửa file của người khác.** Thấy cần sửa thì báo chủ sở hữu.

`ISessionService` (SV2) lo **vòng đời** một phiên: tạo / đọc / gia hạn / xóa.
`ISessionQueryService` (SV1) chỉ **liệt kê** phiên cho trang quản trị. Tách theo hướng
CQRS nên hai phần việc không đụng cùng file.

## ⛔ Hợp đồng dữ liệu

**Tên field MongoDB là camelCase**, ép bằng `[BsonElement("...")]` trên từng property.
Driver mặc định lấy tên property (PascalCase) nên **thêm property mới mà quên
attribute này là tạo field lệch quy ước**, và script seed của SV3 sẽ không khớp.
`categoryId`, `authorId` dùng `[BsonRepresentation(BsonType.ObjectId)]`.

**Key Redis** — dùng hằng và helper ở đầu `Controllers/PostsController.cs`, không ghép
chuỗi bằng tay:

```csharp
CacheKey(id)          // "post:{id}"        — String JSON, TTL 10 phút
ViewsKey(id)          // "post:{id}:views"  — INCR, KHÔNG TTL
ListCachePrefix       // "posts:cat:"       — posts:cat:{categoryId}:p{n}:v{ver}, TTL 3 phút
ListVersionKey        // "posts:ver"        — INCR để vô hiệu hóa cache danh sách, KHÔNG TTL
BumpListVersionAsync()
```

Session: `session:{sessionId}` — **Hash**, TTL 30 phút sliding. Hash chứ không phải
String JSON, vì đề bài yêu cầu rõ *"dùng cấu trúc Hashes lưu Session người dùng"* và
vì cần `HSET` riêng field `lastActive` mà không đọc–ghi lại cả phiên.

Field trong Hash session: `userId`, `username`, `loginAt` (SV2 ghi khi tạo phiên) +
`role`, `lastActive` (SV1 ghi qua `CurrentUserService.TouchAsync`).

## Xác thực & phân quyền

Dùng `ICurrentUserService.GetAsync(HttpContext)` — **không tự đọc cookie/session trong
controller**. Nó trả `CurrentUser(SessionId, UserId, Username, Role, LoginAt)` với
`IsAdmin` sẵn, hoặc null nếu chưa đăng nhập.

`role` nằm trong Hash session nên kiểm tra quyền **không tốn query MongoDB**.

**Hợp đồng cho `SessionAuthMiddleware` (SV2):** `CurrentUserService` có đường tắt đọc
`HttpContext.Items` để khỏi `HGETALL` lần hai trong cùng request. Muốn dùng được thì
middleware phải gán **đủ bộ**, thiếu `Role` là đường tắt bị bỏ qua:

```csharp
context.Items["UserId"]   = session["userId"];
context.Items["Username"] = session["username"];
context.Items["Role"]     = session["role"];     // BẮT BUỘC, thiếu là mất tối ưu
context.Items["LoginAt"]  = session["loginAt"];  // tuỳ chọn
```

## Quy tắc khi viết luồng cache

- **Cache-Aside chỉ ở `GET /api/posts/{id}`.** `GET /api/posts/slug/{slug}` cố ý không
  cache — đừng "tối ưu" thêm cache vào đó, nó sẽ làm lệch phép đo hiệu năng của SV3.
- **Ghi MongoDB trước, xóa Redis sau.** Xóa cache trước rồi mới ghi DB thì một request
  đọc chen vào giữa sẽ nạp lại đúng dữ liệu cũ và giữ nó thêm trọn một vòng TTL.
- **Cache danh sách dùng SỐ PHIÊN BẢN, không SCAN+DEL.** Key phải là
  `posts:cat:{categoryId}:p{page}:v{ver}` với `ver` đọc từ `posts:ver`. Create/Update/
  Delete đã `INCR posts:ver` sẵn, nên chỉ cần đọc đúng số phiên bản là invalidation tự
  hoạt động — không cần thêm method nào vào `ICacheService`.
- **Lock chống stampede bắt buộc có `PX`**: `SET lock:post:{id} 1 NX PX 5000`. Không có
  TTL thì tiến trình giữ khóa chết giữa đường sẽ chặn mọi request sau vĩnh viễn.
- **Không xóa `post:{id}:views` khi xóa mềm bài viết.** Xóa mềm nghĩa là bài có thể
  phục hồi, và lượt xem là số liệu tích lũy — phải để job flush chốt về MongoDB trước.
- **Soft delete lọc bằng `Ne(p => p.IsDeleted, true)`**, không phải `Eq(..., false)` —
  để khớp cả document cũ chưa có field `isDeleted`.

## Việc còn thiếu của SV2

1. **`SessionAuthMiddleware`** — hiện là stub. Gán đủ bộ `HttpContext.Items` như hợp
   đồng ở trên, và refresh TTL (sliding expiration) qua `RefreshSessionAsync`.
2. **`GetById` — luồng Cache-Aside** + khóa chống stampede. Nhớ ghi đè
   `PostResponse.Views` bằng giá trị đọc từ `post:{id}:views` nếu key tồn tại; không
   làm thì UI hiện views đứng im trong khi RedisInsight nhảy số.
3. **`IncrementView`** — `INCR post:{id}:views` + job flush ngược về `posts.views`.
4. **Cache danh sách trang chủ (SCRUM-26)** — đọc `posts:ver` rồi ghép vào key.
5. **TTL session vào `appsettings.json`** (`SessionSettings:TtlMinutes`). Đang hardcode
   30 phút ở `AuthController.SessionTtl`; middleware hardcode lần nữa là lệch.
6. **Header `X-Cache: HIT|MISS`** trong `GetById` — SCRUM-38 của SV3 cần để hiện badge.
   Chốt tên header này rồi nói cho SV3.

## Chạy

```bash
docker compose up -d
dotnet run --project src/NewsCacheSession.Api    # Swagger ở /swagger, health ở /health
```

---

Hợp đồng dữ liệu đầy đủ, barem chấm điểm và kịch bản demo: `AGENTS.md` ở gốc repo.
