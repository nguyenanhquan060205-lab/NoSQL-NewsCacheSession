# Chốt thiết kế dữ liệu (SV1) — những gì Quan và Định cần biết

Ngày chốt: 30/09/2026. Người chốt: Hồ Ngọc Phương Như (SV1 — Data Architect & CRUD Lead).

Đề bài giao SV1 thiết kế cấu trúc DB gốc và mô hình Hashes/Strings trên Redis, nên
file này là hợp đồng dữ liệu chung. Chi tiết đầy đủ ở `mongodb-schema.md` và
`redis-keyspace.md`.

## 1. Tên field trong MongoDB là camelCase — quan trọng nhất

`createdAt`, `passwordHash`, `isDeleted`, `imageUrl`, `categoryId`, `authorId`.

Trước đây model C# không khai `[BsonElement]` nên Mongo lưu tên PascalCase
(`Title`, `CreatedAt`), lệch với comment trong `seed.py`. Nếu seed theo camelCase mà
không sửa model thì API đọc ra bài viết rỗng tiêu đề và `createdAt = 01/01/0001` →
trang chủ trắng, sort sai. Đã ép camelCase bằng `[BsonElement]` trong
`Models/Post.cs`, `Models/User.cs`, `Models/Category.cs`.

**Định (SCRUM-32, seed.py)**: ghi đúng các tên trên. Riêng `categoryId` và `authorId`
phải bọc `ObjectId(...)`, không để string thường — nếu để string thì API lọc theo
chuyên mục (SCRUM-18) sẽ không match bài nào.

**Cả nhóm**: dữ liệu test cũ trong `newsdb` đã ghi bằng tên PascalCase nên không đọc
được nữa — hãy `db.posts.drop()` / `db.users.drop()` rồi seed lại.

## 2. Key Redis đã đổi namespace

| Trước | Bây giờ |
|---|---|
| `post_views:{id}` | `post:{id}:views` |
| (chưa chốt) | `posts:cat:{categoryId}:p{n}` |
| (chưa chốt) | `lock:post:{id}` |

`post:{id}` giữ nguyên. Dùng helper trong `PostsController.cs` thay vì ghép chuỗi tay:
`CacheKey(id)` → `post:{id}`, `ViewsKey(id)` → `post:{id}:views`.
Hằng số `ListCachePrefix = "posts:cat:"` đã để sẵn cho SCRUM-26.

**Quan (SCRUM-20/21/25)**: comment TODO trong `GetById` và `IncrementView` đã được
cập nhật sang tên helper mới.

## 3. Việc cần Quan bổ sung

1. **`ICacheService.RemoveByPrefixAsync(string prefix)`** (SCRUM-23/26). Hiện chỉ có
   `RemoveAsync(key)` nên `Create`/`Update`/`Delete` không xóa được cache danh sách
   `posts:cat:*`. Hệ quả: đăng bài mới xong trang chủ không đổi cho tới khi TTL 3
   phút hết. Interface có method này thì Như sẽ gọi ngay trong cả ba API.
2. **Session hash thêm `role` và `lastActive`** trong `RedisSessionService`.
   `Models/User.cs` đã có field `Role` (mặc định `"user"`); trang admin của Định
   (SCRUM-29) cần đọc role từ session. `lastActive` phục vụ SCRUM-31 (trang quản lý
   phiên đang hoạt động).
3. **`views` trả về cho frontend đang lệch**. `PostResponse.Views` đọc từ MongoDB,
   còn `INCR` đếm trên Redis → trang chi tiết hiện số đứng im trong khi RedisInsight
   nhảy số, thầy nhìn là thấy. Đề nghị trong `GetById`, sau khi lấy bài viết thì
   `GET post:{id}:views` và ghi đè vào `PostResponse.Views` nếu key tồn tại.
4. **TTL session đang hardcode 2 nơi**: `AuthController.SessionTtl` = 30 phút, và
   middleware sẽ hardcode lần nữa khi làm sliding expiration. Lệch nhau là session
   refresh sai. Nên đưa vào `appsettings.json` (`SessionSettings:TtlMinutes`) —
   `Program.cs` là file dùng chung nên cần Quan sửa.
5. **Đăng ký `MongoIndexInitializer`**: đã có file `Data/MongoIndexInitializer.cs`
   tạo unique index cho `posts.slug`, `users.username`, `categories.slug` và compound
   index cho lọc chuyên mục. Cần thêm một dòng vào `Program.cs`, cạnh chỗ
   `AddSingleton<MongoContext>()`:

   ```csharp
   builder.Services.AddHostedService<MongoIndexInitializer>();
   ```

## 4. Việc cần Định biết

- **`GET /api/categories`** đã có (kèm `GET /api/categories/{id}` và
  `/api/categories/slug/{slug}`). Dùng để render menu chuyên mục và dropdown chọn
  chuyên mục ở trang soạn bài.
- **Collection `categories` cần được seed** cùng với 100 bài viết, vì API tạo/sửa bài
  viết giờ kiểm tra `categoryId` có tồn tại thật hay không (trả 400 nếu không).
  Gợi ý vài chuyên mục: Thời sự, Thể thao, Công nghệ, Giải trí, Kinh doanh.
- **Trang chi tiết bài viết dùng `GET /api/posts/{id}`**, không dùng
  `/api/posts/slug/{slug}`. Cache-Aside chỉ nằm ở endpoint theo `{id}` — gọi sai
  endpoint là kịch bản demo "lần 1 ~200ms vs lần 2 <5ms" không chạy.
- **Lọc chuyên mục**: `GET /api/posts?page=1&pageSize=10&categoryId={id}`.
  `api.js` hiện chưa truyền `categoryId`.

## 5. Điểm thiết kế đã bỏ, để khỏi ai hiểu nhầm

- Bỏ `users.email` — form đăng ký chỉ có username + password, thêm email vào sẽ phải
  sửa cả `RegisterRequest` và frontend mà đề không yêu cầu.
- Bỏ `posts.status` (draft/published) — kịch bản demo không có luồng duyệt bài.
- Giữ `GET /api/posts/slug/{slug}` (SCRUM-19) làm endpoint phụ, không cache. Slug vẫn
  unique và vẫn sinh tự động từ tiêu đề, chỉ là demo không đi qua đường này.
