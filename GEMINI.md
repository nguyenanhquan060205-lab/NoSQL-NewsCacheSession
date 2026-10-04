# Hướng dẫn cho Gemini CLI — NoSQL-NewsCacheSession

👉 **Đọc `AGENTS.md` ở gốc repo trước khi sửa code** — bản đầy đủ nằm ở đó.
👉 **Đọc và tuân thủ skill [`.agents/skills/ak-dotnet-backend/SKILL.md`](.agents/skills/ak-dotnet-backend/SKILL.md)** trước khi viết code backend/Redis/MongoDB.

## Quy tắc bắt buộc trước khi bắt đầu (Pre-flight Checklist)
- **Kiểm tra phân công file**: Chỉ sửa file của mình (SV1/SV2/SV3).
- **Kiểm tra skill**: Kích hoạt `ak-dotnet-backend` cùng các tài liệu trong `references/`.
- **Hợp đồng dữ liệu**: BSON camelCase + ObjectId, Redis keyspace chuẩn, DB trước Cache sau.
- **Git**: Kéo `main` mới nhất, làm việc trên branch `SCRUM-...`.

## Ba quy tắc không được vi phạm

1. **Tên field MongoDB là camelCase** (`createdAt`, `passwordHash`, `isDeleted`,
   `imageUrl`, `categoryId`, `authorId`). Model C# ép bằng `[BsonElement("...")]` trên
   từng property — thêm property mới mà quên attribute này là tạo field lệch quy ước.
   `categoryId` và `authorId` lưu dạng **ObjectId**, không phải string.

2. **Key Redis**: `session:{sessionId}` (Hash, TTL 30 phút) ·
   `post:{postId}` (String JSON, TTL 10 phút) · `post:{postId}:views` (INCR, không TTL) ·
   `posts:cat:{categoryId}:p{n}` (TTL 3 phút) · `lock:post:{postId}` (`SET NX PX 5000`).
   Trong C# dùng helper `CacheKey(id)` / `ViewsKey(id)` ở đầu `PostsController.cs`,
   không ghép chuỗi bằng tay.

3. **Cache-Aside nằm ở `GET /api/posts/{id}`**, không phải `/api/posts/slug/{slug}`
   (endpoint slug cố ý không cache). Khi sửa/xóa bài: **ghi MongoDB trước, xóa Redis sau**.

## Phân công — chỉ sửa file của mình

Repo nhóm 3 người, mỗi người sở hữu file riêng. **Không sửa file của người khác**, thấy
cần sửa thì báo chủ sở hữu. Bảng phân công đầy đủ ở mục 4 của `AGENTS.md`.
