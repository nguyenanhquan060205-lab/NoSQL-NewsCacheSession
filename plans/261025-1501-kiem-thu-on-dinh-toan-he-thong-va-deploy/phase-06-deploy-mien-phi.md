---
phase: 6
title: "Deploy miễn phí: Render + Atlas + Redis Cloud + Vercel"
status: pending
priority: P2
effort: "4h"
dependencies: [5]
---

# Phase 6: Deploy miễn phí

## Goal
Đưa bản `main` đã kiểm thử lên mạng, ai cũng mở được, đăng nhập/đọc/sửa bài chạy đúng như local.
Demo chấm điểm vẫn chạy trên máy (G24: server free ngủ sau 15 phút, thức dậy ~1 phút).

## Kiến trúc

```
Trình duyệt ──► Vercel (frontend Vite, src/frontend)
                  │  /api/*  ──rewrite──►  Render Web Service (Docker, API .NET 8, Singapore)
                  │                          ├──► MongoDB Atlas M0 (Singapore, DB newsdb)
                  │                          └──► Redis Cloud free 30 MB
                  └─ /*  ──fallback──► index.html (BrowserRouter)
```
Rewrite cùng origin → cookie `SameSite=Lax` chạy bình thường, không cần sửa CORS (G23).

## Scout pass trước khi làm
- Kiểm tra lại giới hạn hiện hành: [Render free](https://render.com/docs/free),
  [Redis Cloud Essentials](https://redis.io/docs/latest/operate/rc/subscriptions/view-essentials-subscription/essentials-plan-details/),
  [Atlas pricing](https://www.mongodb.com/pricing), [Vercel rewrites](https://vercel.com/docs/rewrites).
- Đọc `reports/04-do-ben.md` phần dung lượng cache (G25) để chọn chính sách eviction.

## File inventory

| File | Hành động | Chủ sở hữu | Ghi chú |
|---|---|---|---|
| `Dockerfile` (gốc repo) | Tạo | Dùng chung → xin phép nhóm | Multi-stage `dotnet/sdk:8.0` → `dotnet/aspnet:8.0`, publish `src/NewsCacheSession.Api`, cổng 8080 |
| `.dockerignore` (gốc repo) | Tạo | Dùng chung → xin phép nhóm | Bỏ `bin/ obj/ node_modules/ scripts/ docs/ plans/ tests/` (riêng `scripts/SeedPosts/data` nặng 46 MB) |
| `src/frontend/vercel.json` | Tạo | Định → xin phép | Rewrite `/api/:path*` → Render, fallback `/(.*)` → `/index.html`, header `Cache-Control: no-store` cho `/api/*` (G26) |
| `scripts/Smoke/smoke_test.py` | Tạo | Bạn | Chỉ dùng thư viện chuẩn Python (chạy được trên Windows của nhóm) |
| `docs/huong-dan-deploy.md` | Tạo | Bạn | Các bước, biến môi trường (chỉ tên, không giá trị), cách rollback |
| `README.md` | Sửa: thêm link deploy | Dùng chung → xin phép | 2–3 dòng |

**Không sửa `Program.cs`:** image `aspnet:8.0` mặc định nghe cổng 8080; Swagger tự tắt ở Production; `/health` đã có.

## Tests Before — smoke test viết trước, chạy được ở mọi môi trường
`scripts/Smoke/smoke_test.py --base-url <URL> --admin-user ... --admin-pass ...` kiểm tra:

| Mức | Bước | Kỳ vọng |
|---|---|---|
| Critical | `GET /health` | 200, `Healthy` cho mongodb và redis |
| Critical | `GET /api/posts?pageSize=1` | `totalItems ≥ 100` |
| Critical | `GET /api/posts/{id}` hai lần | `X-Cache: MISS` → `HIT` |
| Critical | Đăng nhập admin | Có cookie `SessionId`; `GET /api/auth/me` 200 |
| Critical | Tạo bài → sửa → `GET` lại | Lần GET sau khi sửa là MISS và có tiêu đề mới |
| High | Xóa bài vừa tạo | 204 → GET 404 (dọn dữ liệu test) |
| High | `POST /api/posts/{id}/view` | Số lượt xem tăng 1 |
| High | Đăng xuất | `GET /api/auth/me` 401 |
| Medium | `GET <URL>/posts/{id}` (qua Vercel) | 200 HTML (fallback SPA chạy, không 404) |

Chạy lần đầu với API QA `:5135` → phải xanh trước khi làm bất cứ bước deploy nào.

## Implementation Steps
1. Viết `smoke_test.py`, chạy xanh trên `:5135`.
2. Tạo `Dockerfile` + `.dockerignore`; `docker build -t news-api .`; chạy container với biến môi trường
   trỏ vào container QA (`host.docker.internal:27019`, `:6380`) → smoke xanh trên container.
3. **MongoDB Atlas M0:** tạo cluster free ở AWS Singapore; tạo database user mật khẩu mạnh;
   Network Access `0.0.0.0/0` (Render free không có IP tĩnh). Chép dữ liệu: `mongodump` collection
   `posts` + `categories` từ container local → `mongorestore` lên Atlas DB `newsdb`.
   **Không** chép `users` (tránh mang tài khoản demo và hash mật khẩu lên mạng). Dữ liệu ~78.5 MB, vừa 512 MB.
4. **Redis Cloud free:** tạo database ở region gần Singapore nhất có trong danh sách free; đặt
   eviction `volatile-lru` nếu cho chọn (key không TTL như `post:{id}:views`, `posts:ver`,
   `posts:dirty_views` không bị đẩy ra). Chuỗi kết nối dạng `host:port,password=...,abortConnect=false`
   (thêm `ssl=true` nếu bật TLS). Gói free giới hạn 30 kết nối, 100 ops/s.
5. **Render:** New Web Service từ repo GitHub, nhánh `main`, runtime Docker, region Singapore, gói Free,
   Health Check Path `/health`. Biến môi trường: `ASPNETCORE_ENVIRONMENT=Production`, `PORT=8080`,
   `MongoSettings__ConnectionString`, `MongoSettings__DatabaseName=newsdb`, `RedisSettings__ConnectionString`,
   `SessionSettings__TtlMinutes=30`, `CloudinarySettings__CloudName/ApiKey/ApiSecret` (nếu muốn upload ảnh).
6. **Đăng ký admin ngay** sau khi Render lên (G16) — trước khi chia sẻ URL cho bất kỳ ai.
7. Smoke trực tiếp vào URL `*.onrender.com`.
8. **Vercel:** import repo, Root Directory `src/frontend`, framework Vite, build `npm run build`, output `dist`;
   commit `vercel.json` với URL Render thật.
9. Smoke qua URL Vercel (gồm bước fallback SPA). Mở trình duyệt kiểm tra badge HIT/MISS, trang quản lý phiên.
10. Đo cold start: để server ngủ >15 phút rồi gọi `/health`, ghi thời gian.
11. Viết `docs/huong-dan-deploy.md`, thêm link vào `README.md`.

## Refactor
Không đổi hành vi ứng dụng. Chỉ thêm file hạ tầng.

## Tests After / Regression gate
- `smoke_test.py` xanh trên: API QA local, container local, Render, Vercel.
- `dotnet test` và `npx vitest run` trên `main` vẫn xanh.
- **Không** chạy benchmark/tải lên production (Atlas và Redis Cloud free giới hạn ~100 ops/s — G25).

## Rollback
- Render: Rollback về deploy trước trong dashboard. Vercel: Instant Rollback.
- Dữ liệu Atlas: `mongorestore --drop` lại từ bản dump local.
- Gỡ hoàn toàn: xóa service Render/Vercel, cluster Atlas, database Redis Cloud.

## Dependency map
Cần Phase 5 xong và `main` đã merge (deploy từ `main`, Render tự deploy khi `main` có commit mới).

## Success Criteria
- URL Vercel công khai: đọc bài, đăng nhập, admin sửa bài → cache bị xóa, trang quản lý phiên chạy.
- Smoke production xanh; cold start đã đo và ghi trong `docs/huong-dan-deploy.md`.

## Risk Assessment
- Cache bài rất dài làm đầy 30 MB → đã có S5 (JSON gọn hơn) + `volatile-lru`; theo dõi dung lượng trong dashboard Redis Cloud.
- Render hết 750 giờ free/tháng → một service chạy cả tháng ~744 giờ, vừa đủ; không tạo service free thứ hai.
- Vercel cache nhầm response `/api` → header `no-store` + kiểm tra `x-vercel-cache` trong smoke.

## Security Considerations
- Mọi chuỗi kết nối/mật khẩu chỉ nằm trong dashboard Render/Vercel, **không commit**; `docs/huong-dan-deploy.md` chỉ ghi tên biến.
- Atlas mở `0.0.0.0/0` → bắt buộc mật khẩu DB mạnh, user chỉ có quyền `readWrite` trên `newsdb`.
- Ai cũng đăng ký được tài khoản thường và tạo bài → chấp nhận cho đồ án; ghi chú trong tài liệu deploy.

## Todo
- [x] `scripts/Smoke/smoke_test.py` xanh trên API QA
- [x] `Dockerfile` + `.dockerignore` (xin phép), smoke xanh trên container local
- [ ] Atlas M0 + chép `posts`, `categories`
- [ ] Redis Cloud free + chính sách eviction
- [ ] Render Docker + biến môi trường, đăng ký admin ngay
- [ ] Vercel + `vercel.json` (xin phép Định), smoke qua Vercel
- [ ] Đo cold start, viết `docs/huong-dan-deploy.md`
