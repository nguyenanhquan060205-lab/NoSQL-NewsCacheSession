# Frontend — React + Vite (SV3 — Nguyễn Xuân Định)

Trang tin tức: danh sách bài viết, chi tiết bài viết, đăng nhập/đăng ký, trang admin.
Tickets SCRUM-22, 27, 29, 30, 31, 38, 39.

## ⛔ Trang chi tiết phải gọi `GET /api/posts/{id}`

**Không** gọi `/api/posts/slug/{slug}`. Cache-Aside chỉ hiện thực ở endpoint theo
`{id}`; endpoint theo slug là endpoint phụ, **cố ý không cache**.

Gọi sai endpoint thì bước 1 của kịch bản demo — *mở tab Network F12, tải bài viết lần
1 (~200ms từ MongoDB) so với lần 2 (<5ms từ Redis)* — sẽ không có gì để chỉ, vì cả
hai lần đều đi thẳng vào MongoDB.

## Hợp đồng API

| Việc | Endpoint | Quyền |
|---|---|---|
| Danh sách bài viết | `GET /api/posts?page=1&pageSize=10&categoryId={id}` | công khai |
| Chi tiết bài viết (**có cache**) | `GET /api/posts/{id}` | công khai |
| Chi tiết theo slug (không cache) | `GET /api/posts/slug/{slug}` | công khai |
| Tăng lượt xem (INCR) | `POST /api/posts/{id}/view` | công khai |
| Tạo bài | `POST /api/posts` | đăng nhập |
| Sửa / xóa bài | `PUT` / `DELETE /api/posts/{id}` | tác giả **hoặc** admin |
| Danh sách chuyên mục | `GET /api/categories` | công khai |
| Chuyên mục theo id / slug | `GET /api/categories/{id}` · `/slug/{slug}` | công khai |
| **Tạo chuyên mục** | `POST /api/categories` | **admin** |
| Đăng ký / đăng nhập / đăng xuất | `POST /api/auth/register` · `/login` · `/logout` | công khai |
| Phiên hiện tại | `GET /api/auth/me` | đăng nhập |
| **Danh sách phiên đang hoạt động** | `GET /api/auth/sessions` | **admin** |
| **Thu hồi một phiên** | `DELETE /api/auth/sessions/{sessionId}` | **admin** |

`categoryId` là tham số **tùy chọn** của `GET /api/posts` — `api.js` hiện chưa truyền,
cần bổ sung để làm menu lọc chuyên mục (backend SCRUM-18 đã hỗ trợ sẵn).

## Phân quyền — những gì UI phải xử lý

`POST /api/auth/login` và `GET /api/auth/me` đều trả về `role` (`"admin"` hoặc
`"user"`). Dùng nó để ẩn/hiện menu quản trị, **đừng đoán từ username**.

```json
// POST /api/auth/login
{ "sessionId": "...", "userId": "...", "username": "admin1", "role": "admin" }

// GET /api/auth/me
{ "userId": "...", "username": "admin1", "role": "admin",
  "loginAt": "2026-09-30T11:36:05.0000000+00:00", "expiresInSeconds": 1799 }
```

**Tài khoản đăng ký ĐẦU TIÊN của hệ thống tự động là admin.** Không có tài khoản
admin cài sẵn — khi seed DB mới, hãy đăng ký tài khoản admin trước tiên.

**Quy tắc sửa/xóa bài viết:** admin sửa/xóa được mọi bài; người dùng thường chỉ sửa
được bài mình viết. **100 bài seed có `authorId = null` nên chỉ admin sửa/xóa được** —
nếu đăng nhập bằng tài khoản thường mà nút Sửa/Xóa trả 403 thì đó là đúng, không phải
lỗi. UI nên ẩn nút Sửa/Xóa khi `role !== "admin" && post.authorId !== userId`.

Lỗi luôn có dạng `{ "message": "..." }` (tiếng Việt, hiện thẳng lên UI được).
Mã trả về: `401` chưa đăng nhập / phiên hết hạn, `403` không đủ quyền, `404` không
tồn tại, `409` trùng (username, slug chuyên mục), `400` dữ liệu sai.

## Trang quản lý phiên (SCRUM-31)

`GET /api/auth/sessions` trả về mảng, đã sắp theo TTL giảm dần:

```json
[{ "sessionId": "edd691b6-...", "userId": "...", "username": "admin1", "role": "admin",
   "loginAt": "2026-09-30T11:36:05.0000000+00:00",
   "lastActive": "2026-09-30T11:36:05.0000000+00:00",
   "expiresInSeconds": 1798, "isCurrent": true }]
```

- `expiresInSeconds` là số giây còn lại — đếm lùi bằng `setInterval` phía client để
  thấy TTL giảm dần, khớp với bước 3 kịch bản demo (RedisInsight đếm lùi TTL).
- `isCurrent = true` là phiên đang dùng → **ẩn nút Thu hồi**, backend trả `400` nếu cố
  thu hồi phiên của chính mình (dùng chức năng Đăng xuất).
- Sau khi `DELETE` một phiên, người đó bị đăng xuất ngay — `GET /api/auth/me` của họ
  trả `401` lập tức.

## Dạng dữ liệu bài viết

```json
{ "items": [ { "id": "...", "title": "...", "slug": "...", "content": "...",
               "imageUrl": "...", "categoryId": "...", "authorId": null,
               "views": 0, "createdAt": "...", "updatedAt": "..." } ],
  "page": 1, "pageSize": 10, "totalItems": 100, "totalPages": 10 }
```

Chi tiết bài viết trả về thẳng một object như phần tử trong `items`.
`pageSize` bị chặn tối đa **50**; `page`/`pageSize` ≤ 0 bị ép về 1.

## Xác thực bằng session Redis

Đăng nhập xong backend set cookie `SessionId` (HttpOnly) **và** trả `sessionId` trong
body. Axios đã bật `withCredentials: true` nên cookie tự đi kèm — đó là cách dùng
chính. Nếu cookie bị chặn (khác origin, Swagger/Postman) thì gửi header
`X-Session-Id: {sessionId}`, backend đọc được cả hai.

Session TTL 30 phút, sliding. `GET /api/auth/me` trả `401` nghĩa là phiên đã hết hạn
→ điều hướng về trang đăng nhập.

## Badge CACHE HIT/MISS (SCRUM-38)

Backend đã trả header `X-Cache: HIT|MISS` trong `GetById`. Trang chi tiết đọc metadata
`cacheInfo` từ `postsApi.getById`, hiển thị badge và thời gian riêng của GET đo bằng
`performance.now()`. Không suy luận HIT/MISS theo tốc độ, không tính POST tăng view.
Header thiếu/lạ khi GET thành công → `CACHE UNKNOWN`; lỗi GET giữ màn hình lỗi hiện có.
Giữ proxy `/api` same-origin. Deployment khác origin cần nhóm duyệt CORS credentials,
allowed origin và exposed `X-Cache`; không tự sửa backend trong ticket frontend.

## Chạy

```bash
npm install
npm run dev     # Vite proxy chuyển /api/* sang backend, xem vite.config.js
```

---

Chỉ sửa file trong `src/frontend/**` và `scripts/**`. Bảng phân công đầy đủ và hợp
đồng dữ liệu: `AGENTS.md` ở gốc repo.
