# Backend — ASP.NET Core 8 Web API

MongoDB là DB gốc, Redis là HQTCSDL chính của đề tài. Không dùng ORM nào ngoài
MongoDB.Driver; Redis truy cập qua StackExchange.Redis.

## Phân công trong thư mục này

| File | Chủ sở hữu |
|---|---|
| `Models/*`, `DTOs/*`, `Data/MongoIndexInitializer.cs` | SV1 — Hồ Ngọc Phương Như |
| `Controllers/AuthController.cs`, `PostsController.cs`, `CategoriesController.cs` | SV1 — Hồ Ngọc Phương Như |
| ↳ **trừ** `PostsController.GetById` và `PostsController.IncrementView` | SV2 — Nguyễn Anh Quan |
| `Services/*` (cache + session), `Middleware/SessionAuthMiddleware.cs` | SV2 — Nguyễn Anh Quan |
| `Program.cs`, `appsettings.json`, `Data/MongoContext.cs` | dùng chung — hỏi cả nhóm |

**Không sửa file của người khác.** Thấy cần sửa thì báo chủ sở hữu.

## ⛔ Hợp đồng dữ liệu

**Tên field MongoDB là camelCase**, ép bằng `[BsonElement("...")]` trên từng property.
Driver mặc định lấy tên property (PascalCase) nên **thêm property mới mà quên
attribute này là tạo field lệch quy ước**, và script seed của SV3 sẽ không khớp.
`categoryId`, `authorId` dùng `[BsonRepresentation(BsonType.ObjectId)]`.

**Key Redis** — dùng helper ở đầu `Controllers/PostsController.cs`, không ghép chuỗi
bằng tay:

```csharp
CacheKey(id)   // "post:{id}"        — String JSON, TTL 10 phút
ViewsKey(id)   // "post:{id}:views"  — INCR, KHÔNG TTL
ListCachePrefix // "posts:cat:"      — posts:cat:{categoryId}:p{n}, TTL 3 phút
```

Session: `session:{sessionId}` — **Hash**, TTL 30 phút sliding. Hash chứ không phải
String JSON, vì đề bài yêu cầu rõ *"dùng cấu trúc Hashes lưu Session người dùng"* và
vì cần `HSET` riêng field `lastActive` mà không đọc–ghi lại cả phiên.

## Quy tắc khi viết luồng cache

- **Cache-Aside chỉ ở `GET /api/posts/{id}`.** `GET /api/posts/slug/{slug}` cố ý không
  cache — đừng "tối ưu" thêm cache vào đó, nó sẽ làm lệch phép đo hiệu năng của SV3.
- **Ghi MongoDB trước, xóa Redis sau.** Xóa cache trước rồi mới ghi DB thì một request
  đọc chen vào giữa sẽ nạp lại đúng dữ liệu cũ và giữ nó thêm trọn một vòng TTL.
- **Lock chống stampede bắt buộc có `PX`**: `SET lock:post:{id} 1 NX PX 5000`. Không có
  TTL thì tiến trình giữ khóa chết giữa đường sẽ chặn mọi request sau vĩnh viễn.
- **Không xóa `post:{id}:views` khi xóa mềm bài viết.** Xóa mềm nghĩa là bài có thể
  phục hồi, và lượt xem là số liệu tích lũy — phải để job flush chốt về MongoDB trước.
- **Soft delete lọc bằng `Ne(p => p.IsDeleted, true)`**, không phải `Eq(..., false)` —
  để khớp cả document cũ chưa có field `isDeleted`.

## Việc còn thiếu của SV2

1. `ICacheService.RemoveByPrefixAsync(string prefix)` — thiếu thì `Create`/`Update`/
   `Delete` không xóa được cache danh sách `posts:cat:*`, đăng bài mới xong trang chủ
   đứng im 3 phút (SCRUM-23/26).
2. Session hash thêm `role` và `lastActive` (`Models/User.cs` đã có `Role`, mặc định
   `"user"`) — trang admin SCRUM-29 và trang quản lý phiên SCRUM-31 cần.
3. Trong `GetById`, sau khi lấy bài viết thì `GET post:{id}:views` và ghi đè
   `PostResponse.Views` nếu key tồn tại. Không làm thì UI hiện số views đứng im trong
   khi RedisInsight nhảy số — thầy nhìn là thấy.
4. TTL session đang hardcode 30 phút ở `AuthController.SessionTtl`; middleware sẽ
   hardcode lần nữa khi làm sliding expiration. Lệch nhau là refresh sai — nên đưa vào
   `appsettings.json` (`SessionSettings:TtlMinutes`).
5. Thêm một dòng vào `Program.cs` cạnh `AddSingleton<MongoContext>()`:
   `builder.Services.AddHostedService<MongoIndexInitializer>();` — thiếu thì unique
   index của `posts.slug` và `users.username` không được tạo.

## Chạy

```bash
docker compose up -d
dotnet run --project src/NewsCacheSession.Api    # Swagger ở /swagger, health ở /health
```

---

Hợp đồng dữ liệu đầy đủ, barem chấm điểm và kịch bản demo: `AGENTS.md` ở gốc repo.
