# Chốt thiết kế dữ liệu (SV1) — những gì Quan và Định cần biết

Ngày chốt: 30/09/2026. Người chốt: Hồ Ngọc Phương Như (SV1 — Data Architect & CRUD Lead).

Đề bài giao SV1 thiết kế cấu trúc DB gốc và mô hình Hashes/Strings trên Redis, nên
file này là hợp đồng dữ liệu chung. Chi tiết đầy đủ ở `mongodb-schema.md`,
`redis-keyspace.md` và `AGENTS.md` ở gốc repo.

---

## 1. Tên field trong MongoDB là camelCase — quan trọng nhất

`createdAt`, `passwordHash`, `isDeleted`, `imageUrl`, `categoryId`, `authorId`, `role`.

Trước đây model C# không khai `[BsonElement]` nên Mongo lưu tên PascalCase
(`Title`, `CreatedAt`), lệch với comment trong `seed.py`. Nếu seed theo camelCase mà
không sửa model thì API đọc ra bài viết rỗng tiêu đề và `createdAt = 01/01/0001` →
trang chủ trắng, sort sai. Đã ép camelCase bằng `[BsonElement]` trong
`Models/Post.cs`, `Models/User.cs`, `Models/Category.cs`.

Đã kiểm chứng bằng cách chạy thật và soi document trong MongoDB:

```
posts:      _id, title, slug, content, imageUrl, categoryId, authorId, views,
            isDeleted, deletedAt, createdAt, updatedAt
users:      _id, username, passwordHash, role, createdAt
categories: _id, name, slug, description, createdAt
categoryId, authorId: kiểu ObjectId (không phải string)
```

**Định (SCRUM-32, seed.py)**: ghi đúng các tên trên. Riêng `categoryId` và `authorId`
phải bọc `ObjectId(...)`, không để string thường — nếu để string thì API lọc theo
chuyên mục (SCRUM-18) sẽ không match bài nào.

**Cả nhóm**: dữ liệu test cũ ghi bằng tên PascalCase không đọc được nữa — hãy
`db.posts.drop()` / `db.users.drop()` rồi seed lại.

## 2. Key Redis

| Key | Kiểu | TTL |
|---|---|---|
| `session:{sessionId}` | Hash | 30 phút, sliding |
| `post:{postId}` | String JSON | 10 phút |
| `post:{postId}:views` | String số | không TTL |
| `posts:cat:{categoryId}:p{n}:v{ver}` | String JSON list | 3 phút |
| `posts:ver` | String số | không TTL |
| `lock:post:{postId}` | String | 5 giây (`SET NX PX 5000`) |

Đổi so với bản trước: `post_views:{id}` → `post:{id}:views` (gom về cùng namespace).

Dùng helper trong `PostsController.cs` thay vì ghép chuỗi tay: `CacheKey(id)`,
`ViewsKey(id)`, `ListCachePrefix`, `ListVersionKey`, `BumpListVersionAsync()`.

### Field trong Hash session

| Field | Ai ghi |
|---|---|
| `userId`, `username`, `loginAt` | `RedisSessionService.CreateSessionAsync` (SV2) |
| `role`, `lastActive` | `CurrentUserService.TouchAsync` (SV1) |

`role` được ghi vào Hash ngay lúc đăng nhập nên kiểm tra quyền **không tốn query
MongoDB**. Đã kiểm chứng `HSET` thêm field **không làm mất TTL** của phiên.

## 3. Cache danh sách dùng số phiên bản, không SCAN+DEL

Đây là thay đổi thiết kế đáng chú ý nhất, và nó **bỏ được một việc khỏi danh sách của
Quan**.

Cache một bài viết chỉ có một key nên `DEL` là xong. Nhưng cache danh sách rải ra rất
nhiều key: mỗi chuyên mục × mỗi số trang. Muốn xóa hết phải `SCAN` tìm rồi `DEL` từng
cái — O(N) theo số key, phải lặp nhiều lượt, và cần thêm method
`RemoveByPrefixAsync` vào `ICacheService`.

Thay vào đó, số phiên bản `posts:ver` được ghép vào key:
`posts:cat:{categoryId}:p{page}:v{ver}`. Mỗi lần dữ liệu đổi chỉ cần **một lệnh
`INCR`**: toàn bộ key cũ mang số phiên bản nhỏ hơn nên không ai tra tới nữa, và tự
biến mất khi hết TTL 3 phút. Đây là mẫu *cache key versioning*.

`Create` / `Update` / `Delete` đã gọi `BumpListVersionAsync()` sẵn.

**Quan (SCRUM-26)**: chỉ cần đọc `posts:ver` rồi ghép vào key cache danh sách là
invalidation tự hoạt động. **Không cần thêm `RemoveByPrefixAsync` nữa.**

Đánh đổi để nói khi bị hỏi: trong tối đa 3 phút Redis còn giữ cả bản cũ lẫn bản mới
nên tốn thêm bộ nhớ. Với danh sách bài viết thì không đáng kể, và đổi lại được
invalidation O(1) không chặn Redis. `posts:ver` **không đặt TTL**: nếu nó hết hạn rồi
quay về 0 thì các key cache cũ (số phiên bản cao hơn) có thể bị tra lại → đọc dữ liệu cũ.

## 4. Phân quyền — đã xong, Định dùng được ngay

`POST /api/auth/login` và `GET /api/auth/me` đều trả `role` (`"admin"` / `"user"`).

**Tài khoản đăng ký ĐẦU TIÊN tự động là admin** (bootstrap admin) — không có tài khoản
admin cài sẵn, không để lộ mật khẩu admin trong file cấu hình. Cấp quyền cho người khác
về sau: `db.users.updateOne({username:"..."}, {$set:{role:"admin"}})`.

**Quy tắc sửa/xóa bài viết**: admin sửa/xóa được mọi bài; người dùng thường chỉ sửa bài
mình viết. **100 bài seed có `authorId = null` nên chỉ admin sửa/xóa được** — trước đây
ai đăng nhập cũng xóa được cả 100 bài, giờ không còn.

## 5. Endpoint mới

| Endpoint | Quyền | Phục vụ |
|---|---|---|
| `GET /api/categories` · `/{id}` · `/slug/{slug}` | công khai | menu chuyên mục, dropdown soạn bài |
| `POST /api/categories` | admin | trang admin tạo chuyên mục (trước đây chỉ script seed tạo được) |
| `GET /api/auth/sessions` | admin | **SCRUM-31** — danh sách phiên đang hoạt động kèm TTL đếm lùi |
| `DELETE /api/auth/sessions/{sessionId}` | admin | **SCRUM-31** — thu hồi phiên, buộc đăng xuất |

`GET /api/auth/sessions` dùng `SCAN` chứ **không** dùng `KEYS`: `KEYS` quét toàn bộ
keyspace trong một lệnh và chặn Redis single-thread suốt thời gian đó.

Câu để trả lời phản biện: *"Cách này có mở rộng được không?"* — với 20–50 session theo
định mức đề bài thì `SCAN` thừa sức. Ở quy mô thật, cách đúng là duy trì thêm một Set
`user_sessions:{userId}` chứa các sessionId để liệt kê không cần quét keyspace; đánh
đổi là phải cập nhật Set mỗi lần tạo/xóa phiên.

## 6. Việc còn lại của Quan

1. **`SessionAuthMiddleware`** (đang là stub) — gán đủ bộ `HttpContext.Items`:
   `UserId`, `Username`, **`Role`** (bắt buộc), `LoginAt` (tuỳ chọn). `CurrentUserService`
   có đường tắt đọc Items để khỏi `HGETALL` lần hai trong cùng request; thiếu `Role` là
   đường tắt bị bỏ qua. Kèm refresh TTL sliding.
2. **`GetById`** — luồng Cache-Aside + lock chống stampede. Nhớ ghi đè
   `PostResponse.Views` bằng giá trị đọc từ `post:{id}:views` nếu key tồn tại; không làm
   thì UI hiện views đứng im trong khi RedisInsight nhảy số.
3. **`IncrementView`** — `INCR post:{id}:views` + job flush ngược về `posts.views`.
4. **Cache danh sách (SCRUM-26)** — đọc `posts:ver`, ghép vào key.
5. **Header `X-Cache: HIT|MISS`** trong `GetById` — SCRUM-38 của Định cần. Chốt tên
   header rồi nói cho Định, đừng để bạn ấy tự đoán.
6. **TTL session vào `appsettings.json`** (`SessionSettings:TtlMinutes`) — đang hardcode
   30 phút ở `AuthController.SessionTtl`, middleware hardcode lần nữa là lệch.

## 7. Việc còn lại của Định

- **Seed collection `categories`** cùng 100 bài viết. API tạo/sửa bài viết kiểm tra
  `categoryId` có tồn tại thật, không có chuyên mục thì trả 400. Gợi ý: Thời sự, Thể
  thao, Công nghệ, Giải trí, Kinh doanh.
- **Đăng ký tài khoản admin TRƯỚC TIÊN** sau khi seed DB mới, vì user đầu tiên mới
  thành admin.
- **Trang chi tiết dùng `GET /api/posts/{id}`**, không phải `/slug/{slug}` — Cache-Aside
  chỉ nằm ở endpoint theo id.
- **`api.js` truyền `categoryId`** vào `GET /api/posts` để làm menu lọc chuyên mục.
- **Ẩn nút Sửa/Xóa** khi `role !== "admin" && post.authorId !== userId`, tránh người
  dùng bấm vào rồi nhận 403.
- **Upload ảnh (SCRUM-39)** chưa chốt: dùng URL ngoài (picsum) hay cần endpoint upload
  file ở backend? Nếu cần endpoint thì nói sớm, đó là việc của SV1.

## 8. Điểm thiết kế đã bỏ, để khỏi ai hiểu nhầm

- Bỏ `users.email` — form đăng ký chỉ có username + password, thêm email vào sẽ phải
  sửa cả `RegisterRequest` và frontend mà đề không yêu cầu.
- Bỏ `posts.status` (draft/published) — kịch bản demo không có luồng duyệt bài.
- Giữ `GET /api/posts/slug/{slug}` (SCRUM-19) làm endpoint phụ, **cố ý không cache** —
  đây là mốc đo "trước" để Định so sánh hiệu năng. Slug vẫn unique và vẫn sinh tự động.

## 9. Đã kiểm chứng bằng cách chạy thật

Toàn bộ mục 1–5 đã được test end-to-end qua HTTP với MongoDB + Redis thật:
**54/54 test PASS**. Gồm bootstrap admin, 401/403/404/409 đúng chỗ, slug bỏ dấu tiếng
Việt và hậu tố `-2` khi trùng, soft delete biến khỏi danh sách, `pageSize` bị chặn về
50, lọc chuyên mục, `posts:ver` tăng đúng, TTL session không bị mất khi ghi thêm field,
thu hồi phiên làm `/me` trả 401 ngay.
