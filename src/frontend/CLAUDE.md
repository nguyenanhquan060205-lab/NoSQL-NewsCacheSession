# Frontend — React + Vite (SV3 — Nguyễn Xuân Định)

Trang tin tức: danh sách bài viết, chi tiết bài viết, đăng nhập/đăng ký, trang admin
CRUD. Tickets SCRUM-22, 27, 29, 30, 31, 38, 39.

## ⛔ Trang chi tiết phải gọi `GET /api/posts/{id}`

**Không** gọi `/api/posts/slug/{slug}`. Cache-Aside chỉ hiện thực ở endpoint theo
`{id}`; endpoint theo slug là endpoint phụ, **cố ý không cache**.

Gọi sai endpoint thì bước 1 của kịch bản demo — *mở tab Network F12, tải bài viết lần
1 (~200ms từ MongoDB) so với lần 2 (<5ms từ Redis)* — sẽ không có gì để chỉ, vì cả
hai lần đều đi thẳng vào MongoDB.

## Hợp đồng API

| Việc | Endpoint |
|---|---|
| Danh sách bài viết | `GET /api/posts?page=1&pageSize=10&categoryId={id}` |
| Chi tiết bài viết (**có cache**) | `GET /api/posts/{id}` |
| Tăng lượt xem (INCR) | `POST /api/posts/{id}/view` |
| Tạo / sửa / xóa bài | `POST /api/posts` · `PUT /api/posts/{id}` · `DELETE /api/posts/{id}` |
| Danh sách chuyên mục | `GET /api/categories` |
| Chuyên mục theo slug | `GET /api/categories/slug/{slug}` |
| Đăng ký / đăng nhập / đăng xuất | `POST /api/auth/register` · `/login` · `/logout` |
| Phiên hiện tại | `GET /api/auth/me` |

`categoryId` là tham số **tùy chọn** của `GET /api/posts` — `api.js` hiện chưa truyền,
cần bổ sung để làm được menu lọc chuyên mục (SCRUM-18 backend đã hỗ trợ sẵn).

### Dạng dữ liệu trả về

Danh sách bài viết:
```json
{ "items": [ { "id": "...", "title": "...", "slug": "...", "content": "...",
               "imageUrl": "...", "categoryId": "...", "authorId": null,
               "views": 0, "createdAt": "...", "updatedAt": "..." } ],
  "page": 1, "pageSize": 10, "totalItems": 100, "totalPages": 10 }
```

Chi tiết bài viết trả về thẳng một object như phần tử trong `items`.
Lỗi luôn có dạng `{ "message": "..." }` (tiếng Việt, hiện thẳng lên UI được).

`pageSize` bị chặn tối đa **50** ở backend.

## Xác thực bằng session Redis

Đăng nhập xong backend set cookie `SessionId` (HttpOnly) **và** trả `sessionId` trong
body. Axios đã bật `withCredentials: true` nên cookie tự đi kèm — đó là cách dùng
chính. Nếu cookie bị chặn (khác origin, chạy trên máy khác) thì gửi header
`X-Session-Id: {sessionId}`, backend đọc được cả hai.

Session TTL 30 phút, sliding — mỗi request hợp lệ lại gia hạn về 30 phút. `GET
/api/auth/me` trả 401 nghĩa là phiên đã hết hạn, cần điều hướng về trang đăng nhập.

## Badge CACHE HIT/MISS (SCRUM-38)

Backend chưa trả về thông tin hit/miss. Cần SV2 thêm header (ví dụ `X-Cache: HIT`
hoặc `MISS`) trong `GetById` — thống nhất với Quan trước khi làm UI, đừng tự đoán
tên header.

## Chạy

```bash
npm install
npm run dev     # Vite proxy chuyển /api/* sang backend, xem vite.config.js
```

---

Chỉ sửa file trong `src/frontend/**` và `scripts/**`. Bảng phân công đầy đủ và hợp
đồng dữ liệu: `AGENTS.md` ở gốc repo.
