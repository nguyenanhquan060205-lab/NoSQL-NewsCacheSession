# Thiết kế schema MongoDB

Database dùng 3 collection: `users`, `categories`, `articles`.

## users
```json
{
  "_id": "ObjectId",
  "username": "string, unique",
  "password_hash": "string",
  "email": "string",
  "role": "admin | user",
  "created_at": "datetime"
}
```

## categories
```json
{
  "_id": "ObjectId",
  "name": "string",
  "slug": "string, unique",
  "description": "string"
}
```

## articles
```json
{
  "_id": "ObjectId",
  "title": "string",
  "slug": "string, unique",
  "content": "string",
  "category_id": "ObjectId, ref categories",
  "author_id": "ObjectId, ref users",
  "status": "draft | published",
  "views": "integer, default 0",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Index cần tạo
| Collection | Field | Loại | Lý do |
|---|---|---|---|
| articles | slug | unique | tra cứu bài viết theo URL |
| articles | category_id | thường | lọc danh sách bài viết theo chuyên mục |
| users | username | unique | đăng nhập, tránh trùng tài khoản |

## Quan hệ dữ liệu
- Một `article` thuộc về một `category` (qua `category_id`).
- Một `article` có một tác giả (qua `author_id` trỏ tới `users`).
- Dùng reference (ObjectId) thay vì embed toàn bộ document, vì `users` và `categories` được nhiều `articles` dùng chung — embed sẽ gây trùng lặp dữ liệu khi category/tên tác giả thay đổi.
