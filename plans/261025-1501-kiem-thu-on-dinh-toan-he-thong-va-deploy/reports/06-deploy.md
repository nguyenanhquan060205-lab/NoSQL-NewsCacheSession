# Phase 6 — Deploy miễn phí (26/10/2026)

| | Giá trị |
|---|---|
| Web | https://no-sql-news-cache-session.vercel.app (Vercel, Root Directory `src/frontend`) |
| API | https://newscachesession-api.onrender.com (Render Free, Docker, build từ `main`) |
| MongoDB | Atlas Free `Cluster0`, DB `newsdb`: 10 101 bài (10 000 chưa xóa, không có bài VnExpress), 7 chuyên mục, đủ 3 index |
| Redis | Redis Cloud Free 30 MB, Redis 8.6.2, `maxmemory_policy: volatile-lru`, TLS tắt |

## Kiểm tra trên bản thật

```
smoke_test.py --base-url https://newscachesession-api.onrender.com          OK — 8/8
smoke_test.py --base-url https://no-sql-news-cache-session.vercel.app --spa-url ...   OK — 9/9
/api qua Vercel (2 lần): cache-control: no-store · x-cache: MISS → HIT · x-vercel-cache: MISS cả 2
Trang chủ: x-robots-tag: noindex, nofollow + <meta name="robots" content="noindex, nofollow">
F5 /admin/posts: 200 text/html
Cookie qua Vercel: max-age=1800; path=/; secure; samesite=lax; httponly
User thường POST /api/posts: 403 "Bản demo trực tuyến chỉ cho quản trị viên đăng bài và tải ảnh."
Cold start sau 17 phút không có request: 33,6 s; gọi lại ngay: 0,22 s
```

Trước khi đưa lên Render: chạy image `main` trên máy với đúng bộ biến môi trường production → `/health`
Healthy (Atlas + Redis Cloud), MISS → HIT. Dữ liệu thử (bài smoke test, tài khoản tạm kiểm tra `AdminOnly`)
đã xóa khỏi Atlas và Redis Cloud sau mỗi lần kiểm tra.

## Sự cố khi deploy

| Sự cố | Nguyên nhân | Xử lý |
|---|---|---|
| Deploy Render treo 15 phút rồi `Timed Out` (2 lần) dù app đã chạy | Ô **Health Check Path** gõ nhầm `/heath` → app trả 404 | Sửa thành `/health`, Manual Deploy → live |
| (cùng lúc) app nghe `[::]:8080` | Image `aspnet:8.0` mặc định chỉ mở socket IPv6; Render yêu cầu bind `0.0.0.0` | `Dockerfile` đặt `ASPNETCORE_URLS=http://0.0.0.0:8080` (PR #26) — đúng theo tài liệu Render, nhưng không phải nguyên nhân chính |
| Chuỗi kết nối Atlas mới không có tham số | Atlas UI mới kết thúc bằng `/` | Nối `?retryWrites=true&w=majority&serverSelectionTimeoutMS=5000` (dùng `?`, không phải `&`) |

## Bảo mật còn mở (Quân chấp nhận)

- Mật khẩu Atlas và Redis Cloud đã nằm trong lịch sử chat; Atlas mở `0.0.0.0/0`. Quân chọn không đổi mật khẩu.
- Bộ biến production lưu ở `.env.render` (gitignore); file Atlas tự sinh `docs/atlas-credentials.env` cũng đã bị gitignore.
