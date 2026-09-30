# Thiết kế schema MongoDB

Database `newsdb` dùng 3 collection: `users`, `categories`, `posts`.

## Quy ước đặt tên field

Tên field trong MongoDB dùng **camelCase** (`createdAt`, `passwordHash`, `isDeleted`).
Đây là quy ước bắt buộc của cả nhóm, được ép trong code bằng `[BsonElement("...")]`
trên từng property của model C# — không dựa vào tên property mặc định (vốn là
PascalCase). Lý do:

- Khớp với JSON mà API trả về frontend → đọc document trong Compass/Studio 3T thấy
  giống hệt response, dễ đối chiếu khi debug.
- Khớp với script seed viết bằng Python (`scripts/SeedPosts/seed.py`) → SV3 nạp dữ
  liệu bằng đúng tên field này, không cần map lại.

> ⚠️ Nếu ghi dữ liệu vào Mongo bằng tên field khác (PascalCase hay snake_case), API
> sẽ deserialize ra giá trị rỗng: bài viết không có tiêu đề, `createdAt` = `01/01/0001`.

## users
```json
{
  "_id": "ObjectId",
  "username": "string, unique",
  "passwordHash": "string (BCrypt)",
  "role": "admin | user",
  "createdAt": "datetime"
}
```

`role` mặc định là `"user"`. **Tài khoản đăng ký đầu tiên của hệ thống tự động thành
`"admin"`** (bootstrap admin) — nhờ vậy luôn có ít nhất một người quản trị mà không phải
chèn tay vào DB, cũng không để lọ mật khẩu admin trong file cấu hình (vịn của cách
seed sẵn tài khoản admin/admin123).

Muốn cấp quyền admin cho người khác về sau:

```js
db.users.updateOne({ username: "ten_tai_khoan" }, { $set: { role: "admin" } })
```

Quyền được dùng ở: `GET/DELETE /api/auth/sessions` (trang quản trị phiên, SCRUM-31),
`POST /api/categories`, và quyền sửa/xóa bài viết của người khác (SCRUM-29).
`role` cũng được ghi vào Hash `session:{id}` lúc đăng nhập để kiểm tra quyền không
tốn query MongoDB — xem `redis-keyspace.md`.

## categories
```json
{
  "_id": "ObjectId",
  "name": "string",
  "slug": "string, unique",
  "description": "string | null",
  "createdAt": "datetime"
}
```

## posts
```json
{
  "_id": "ObjectId",
  "title": "string",
  "slug": "string, unique",
  "content": "string",
  "imageUrl": "string | null",
  "categoryId": "ObjectId | null, ref categories",
  "authorId": "ObjectId | null, ref users",
  "views": "integer, default 0",
  "isDeleted": "boolean, default false",
  "deletedAt": "datetime | null",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

`categoryId` và `authorId` lưu **dạng ObjectId** (không phải string) để đúng nghĩa
reference — script seed phải bọc `ObjectId(...)` khi ghi. `authorId` được phép null
với dữ liệu seed (bài viết không có tác giả cụ thể).

`views` là lượt xem **đã chốt** vào MongoDB. Số đếm thời gian thực nằm ở Redis
(`post:{id}:views`, dùng `INCR`) và được job của SV2 flush ngược về field này —
xem `redis-keyspace.md`.

`isDeleted` và `deletedAt` phục vụ cơ chế soft delete: API xóa chỉ đánh dấu bài viết
đã bị xóa, không xóa vật lý document khỏi MongoDB. Các truy vấn đọc lọc bằng
`isDeleted != true` (chứ không phải `isDeleted == false`) để tương thích với document
cũ chưa có trường này.

## Index cần tạo

Được tạo tự động lúc khởi động ứng dụng bởi `Data/MongoIndexInitializer.cs`.

| Collection | Field | Loại | Lý do |
|---|---|---|---|
| posts | `slug` | unique | tra cứu bài viết theo URL; chặn trùng slug ở tầng DB vì hàm sinh slug chỉ chống trùng bằng query (còn race condition) |
| posts | `categoryId` + `createdAt` desc | compound | lọc danh sách theo chuyên mục rồi sắp bài mới nhất (SCRUM-18) |
| posts | `createdAt` desc | thường | trang chủ sắp bài mới nhất trước |
| users | `username` | unique | đăng nhập; chặn trùng tài khoản ở tầng DB, không chỉ dựa vào kiểm tra trong `AuthController.Register` |
| categories | `slug` | unique | URL chuyên mục thân thiện |

## Quan hệ dữ liệu

- Một `post` thuộc về một `category` (qua `categoryId`).
- Một `post` có một tác giả (qua `authorId` trỏ tới `users`).

Dùng **reference** (ObjectId) thay vì embed toàn bộ document, vì `users` và
`categories` được nhiều `posts` dùng chung — embed sẽ gây trùng lặp dữ liệu và phải
cập nhật hàng loạt khi tên chuyên mục hoặc tên tác giả thay đổi.

Đánh đổi: đọc bài viết kèm tên chuyên mục/tác giả cần thêm một truy vấn (hoặc
`$lookup`). Với luồng Cache-Aside thì chi phí này chỉ trả một lần rồi được cache lại
trong Redis, nên chấp nhận được.
