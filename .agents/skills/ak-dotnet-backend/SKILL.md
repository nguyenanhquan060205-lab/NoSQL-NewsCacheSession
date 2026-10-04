---
name: ak-dotnet-backend
description: Build ASP.NET Core Web API backends (.NET 8/9, C#) with Redis caching (Cache-Aside, Hash sessions, atomic INCR counters, distributed locks, versioned list invalidation) and MongoDB (camelCase BSON mappings, ObjectId handling, compound indexes).
user-invocable: true
when_to_use: "Invoke when working on ASP.NET Core Web API, C# backend logic, Redis caching strategies, or MongoDB persistence."
category: backend
keywords: [dotnet, csharp, aspnetcore, redis, mongodb, cache-aside, nosql]
license: MIT
argument-hint: "[task or component]"
metadata:
  author: agentkit
  version: "1.0.0"
---

# ASP.NET Core Backend & NoSQL (Redis + MongoDB) Skill

Chuyên môn hóa cho việc xây dựng và tối ưu backend ASP.NET Core (.NET 8/9 C#) kết hợp MongoDB (cơ sở dữ liệu gốc) và Redis (hệ thống caching & quản lý phiên phân tán).

## 1. Nguyên tắc cốt lõi & Hợp đồng dữ liệu

### 1.1. MongoDB (Database gốc)
- **Tên field bắt buộc là camelCase**: Driver C# mặc định dùng PascalCase theo tên thuộc tính C#. Bắt buộc phải thêm attribute `[BsonElement("...")]` trên từng property trong các Models (`Models/Post.cs`, `Models/User.cs`, `Models/Category.cs`).
- **Khóa ngoại và ID**: `categoryId`, `authorId`, và `_id` phải dùng `[BsonRepresentation(BsonType.ObjectId)]` và lưu dạng `ObjectId` trong MongoDB, tuyệt đối không lưu string thô.
- **Thứ tự ghi nhận khi sửa/xóa**: Luôn **ghi MongoDB trước, xóa/vô hiệu hóa Redis sau** để tránh race condition nạp dữ liệu cũ vào cache.

### 1.2. Redis Keyspace (StackExchange.Redis)
Tuân thủ nghiêm ngặt bảng keyspace và thời gian sống (TTL):

| Key Pattern | Kiểu dữ liệu | TTL | Mục đích |
|---|---|---|---|
| `session:{sessionId}` | Hash | 30 phút (sliding) | Quản lý phiên: `userId`, `username`, `loginAt`, `role`, `lastActive` |
| `post:{postId}` | String (JSON) | 10 phút | Cache chi tiết bài viết (Cache-Aside) |
| `post:{postId}:views` | String (số nguyên) | Không TTL | Bộ đếm lượt xem bằng atomic `INCR` |
| `posts:cat:{categoryId}:p{n}:v{ver}` | String (JSON array) | 3 phút | Cache danh sách bài viết theo chuyên mục/trang |
| `posts:ver` | String (số nguyên) | Không TTL | Số phiên bản danh sách bài viết (`INCR` để vô hiệu hóa toàn bộ cache danh sách O(1)) |
| `lock:post:{postId}` | String | 5 giây | Khóa phân tán chống Cache Stampede (`SET NX PX 5000`) |

> **Quy tắc vàng:** Không ghép chuỗi key thủ công rải rác. Sử dụng các helper định nghĩa tập trung (ví dụ trong `PostsController`: `CacheKey(id)`, `ViewsKey(id)`, `BumpListVersionAsync()`).

---

## 2. Kiến trúc & Các Luồng Xử Lý Quan Trọng

### 2.1. Triển khai Cache-Aside (`GET /api/posts/{id}`)
1. **Kiểm tra Redis**: Gọi `GET post:{id}`.
   - **Cache HIT**: Ghi đè `views` bằng giá trị từ `post:{id}:views` (nếu có key views) -> Trả về kết quả kèm response header `X-Cache: HIT`.
2. **Cache MISS**:
   - Thử chiếm khóa phân tán: `SET lock:post:{id} <ownerId> NX PX 5000`.
   - Nếu không lấy được khóa (đang có request khác nạp): Chờ 50-100ms và thử đọc lại cache.
   - Nếu lấy được khóa:
     - Đọc bài viết từ MongoDB (`posts.Find(x => x.Id == id && !x.IsDeleted)`).
     - Nếu không tìm thấy: Trả về 404 (có thể cache rỗng ngắn hạn chống Cache Penetration).
     - Ghi bài viết vào Redis: `SET post:{id} <json> EX 600`.
     - Giải phóng khóa (chỉ xóa nếu đúng ownerId qua Lua script).
     - Trả về kết quả kèm response header `X-Cache: MISS`.

### 2.2. Atomic Counter Lượt Xem (`INCR`)
- Khi người dùng đọc bài viết hoặc gọi `POST /api/posts/{id}/view`:
  - Thực thi atomic `INCR post:{id}:views`.
  - Không ghi trực tiếp vào MongoDB trên từng lượt đọc.
  - Sử dụng Background Worker (`IHostedService`) hoặc flush định kỳ để đồng bộ số views về collection MongoDB:
    `UpdateOne(x => x.Id == id, Builders<Post>.Update.Set(x => x.Views, redisViews))`.

### 2.3. Vòng Đời Phiên Người Dùng (Session Management qua Hashes)
- Dùng cấu trúc **Redis Hash** thay vì String JSON để cho phép cập nhật từng field (`HSET lastActive ...`) mà không cần nạp-ghi toàn bộ dữ liệu.
- Trong `SessionAuthMiddleware`:
  1. Trích xuất `sessionId` từ HTTP header hoặc Cookie.
  2. Tra cứu `HGETALL session:{sessionId}` từ Redis.
  3. Nếu phiên hợp lệ:
     - Gán thông tin vào context:
       ```csharp
       context.Items["UserId"]   = session["userId"];
       context.Items["Username"] = session["username"];
       context.Items["Role"]     = session["role"];
       context.Items["LoginAt"]  = session["loginAt"];
       ```
     - Gia hạn sliding expiration: `EXPIRE session:{sessionId} 1800`.
     - Cập nhật thời điểm tương tác gần nhất: `HSET session:{sessionId} lastActive <now>`.

---

## 3. Điều Hướng Tài Liệu Tham Khảo (References)

- **[redis-patterns.md](references/redis-patterns.md)**: Hướng dẫn chi tiết triển khai Cache-Aside, Distributed Lock chống stampede, Hash session và Versioned list invalidation.
- **[mongodb-guidelines.md](references/mongodb-guidelines.md)**: Quy chuẩn mapping BSON camelCase, tạo Index tối ưu, tránh N+1 và xử lý transaction/bulk write.
- **[session-and-auth.md](references/session-and-auth.md)**: Thiết kế middleware xác thực phiên, sliding expiration, phân quyền role và hợp đồng `HttpContext.Items`.
