# Hướng dẫn deploy miễn phí

Bản deploy để ai cũng mở được web. **Demo chấm điểm vẫn chạy trên máy**: server free ngủ sau 15 phút
không có request và mất khoảng 1 phút để thức dậy, nên lần tải đầu không minh họa được MISS/HIT.

```
Trình duyệt ──► Vercel (frontend Vite, src/frontend)
                  │  /api/*, /health ──rewrite──► Render Web Service (Docker, API .NET 8)
                  │                                 ├──► MongoDB Atlas (gói Free, DB newsdb)
                  │                                 └──► Redis Cloud (gói Free 30 MB)
                  └─ /* ──fallback──► index.html (React Router, F5 trang con không 404)
```

Frontend gọi `/api` cùng origin với trang (Vercel rewrite sang Render), nên cookie `SessionId`
(`SameSite=Lax`) chạy bình thường mà không phải sửa CORS.

## Giới hạn gói free (kiểm lại ngày 26/10/2026)

| Dịch vụ | Giới hạn đáng chú ý | Nguồn |
|---|---|---|
| Render Free | Ngủ sau 15 phút không có request, thức dậy ~1 phút; 750 giờ/tháng cho cả workspace (một service chạy cả tháng ~744 giờ — **chỉ tạo một service free**); không có ổ đĩa lưu trữ | [render.com/docs/free](https://render.com/docs/free) |
| Redis Cloud Free | 30 MB, 30 kết nối, 100 ops/s, 5 GB băng thông/tháng | [Essentials plan details](https://redis.io/docs/latest/operate/rc/subscriptions/view-essentials-subscription/essentials-plan-details/) |
| MongoDB Atlas Free | 1 cluster free mỗi project, không backup, replica set 3 node cố định | [Free cluster limitations](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/) |
| Vercel | Rewrite sang origin ngoài **tôn trọng header cache của upstream** → phải chặn cache `/api` rõ ràng | [vercel.com/docs/rewrites](https://vercel.com/docs/rewrites) |

**Không chạy benchmark hay test tải lên bản deploy** — 100 ops/s của Redis Cloud sẽ bị vượt ngay.

Dung lượng Redis: bài dài nhất chiếm ~393 KB/key, trung bình ~15 KB. Trong 10 phút TTL, 30 MB chứa được
khoảng 2 000 bài khác nhau — đủ cho bản demo. Đặt eviction `volatile-lru` để Redis chỉ đẩy key **có TTL**
khi đầy; các key không TTL (`post:{id}:views`, `posts:ver`, `posts:dirty_views`) không bao giờ bị đẩy ra.

## Bản đang chạy (26/10/2026)

| | URL |
|---|---|
| Web (Vercel) | <https://no-sql-news-cache-session.vercel.app> |
| API (Render, Docker) | <https://newscachesession-api.onrender.com> — `/health` báo Healthy cho MongoDB Atlas và Redis Cloud |

Đã kiểm tra trên bản thật: smoke test qua Vercel 9/9 (đăng nhập, MISS → HIT, sửa bài xóa cache, lượt xem,
F5 trang con, xóa, đăng xuất); `/api` qua Vercel luôn `x-vercel-cache: MISS`; header + thẻ meta `noindex`;
cookie `SessionId` có `secure; samesite=lax; httponly`; tài khoản thường tạo bài nhận 403 (`AdminOnly`).
Dữ liệu: 10 000 bài Wikipedia/Wikinews + 7 chuyên mục. Tài khoản do Quân quản lý — không ghi ở đây.

## 0. Điều kiện trước khi deploy

- PR `develop → main` đã merge — Render deploy từ nhánh `main` và tự deploy lại mỗi khi `main` có commit mới.
- Máy có Docker (dùng image `mongo:7.0` để chép dữ liệu, khỏi cài `mongodump` riêng).
- Lệnh trong tài liệu viết cho bash (macOS/Linux hoặc Git Bash trên Windows). PowerShell: thay
  `export TEN=giatri` bằng `$env:TEN="giatri"` và `"$PWD/..."` bằng `"${PWD}/..."`.

## 1. MongoDB Atlas

1. Tạo cluster **Free**, nhà cung cấp AWS, region **Singapore (ap-southeast-1)**.
2. *Database Access* → tạo database user, mật khẩu mạnh (tự sinh), quyền **readWrite** trên DB `newsdb`.
3. *Network Access* → `0.0.0.0/0` (Render free không có IP tĩnh — vì vậy mật khẩu DB phải mạnh).
4. *Connect → Drivers* → chép chuỗi `mongodb+srv://...`, thêm tham số để request không treo 30 giây
   khi Atlas chập chờn (giống chuỗi mặc định trong `appsettings.json`):
   `mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority&serverSelectionTimeoutMS=5000`
5. Chép dữ liệu — **chỉ** `posts` và `categories`, **không** chép `users` (khỏi mang tài khoản demo và
   hash mật khẩu lên mạng), và **bỏ 150 bài tóm tắt RSS VnExpress** (văn bản và ảnh của báo có bản quyền,
   ảnh còn tải thẳng từ CDN của VnExpress — chỉ để chạy demo trên máy). Chạy ở gốc repo khi stack local đang bật:

   ```bash
   mkdir -p atlas-dump
   docker exec news-mongo mongodump --quiet --db newsdb --collection posts \
     --query '{"slug":{"$not":{"$regex":"^real-vnexpress"}}}' --gzip --archive=/tmp/posts.gz
   docker exec news-mongo mongodump --quiet --db newsdb --collection categories --gzip --archive=/tmp/categories.gz
   docker cp news-mongo:/tmp/posts.gz atlas-dump/ && docker cp news-mongo:/tmp/categories.gz atlas-dump/

   # ATLAS_URI = chuỗi ở bước 4; đặt trong biến môi trường, đừng gõ thẳng vào lệnh để khỏi lưu vào history
   docker run --rm -v "$PWD/atlas-dump:/dump" mongo:7.0 mongorestore --uri "$ATLAS_URI" --gzip --archive=/dump/posts.gz
   docker run --rm -v "$PWD/atlas-dump:/dump" mongo:7.0 mongorestore --uri "$ATLAS_URI" --gzip --archive=/dump/categories.gz
   rm -rf atlas-dump
   ```

   Kỳ vọng (đã thử cùng lệnh vào một Mongo khác): `10101 document(s) restored` (10 000 bài chưa xóa:
   9 900 Wikipedia + 100 Wikinews, không còn ảnh `vnecdn.net`), `7 document(s) restored`; index
   `ux_posts_slug`, `ix_posts_category_createdAt`, `ix_posts_createdAt` đi theo. Dữ liệu ~78 MB, vừa gói free.

## 2. Redis Cloud

1. Tạo database gói **Free (30 MB)**, chọn region gần Singapore nhất có trong danh sách free.
2. *Configuration* → **Eviction policy: `volatile-lru`** (nếu được chọn).
3. Chép *Public endpoint* (`host:port`) và mật khẩu user `default`. Chuỗi kết nối cho StackExchange.Redis:
   `host:port,password=<mật khẩu>,abortConnect=false` (thêm `,ssl=true` nếu bật TLS cho database).

## 3. Render (API)

*New → Web Service* → chọn repo GitHub:

| Mục | Giá trị |
|---|---|
| Name | **`newscachesession-api`** → URL `https://newscachesession-api.onrender.com` (đã ghi sẵn trong `src/frontend/vercel.json`) |
| Branch | `main` |
| Runtime / Language | **Docker** (tự nhận `Dockerfile` ở gốc repo) |
| Region | Singapore |
| Instance type | Free |
| Health Check Path | `/health` |

Biến môi trường (chỉ nhập trong dashboard Render, **không commit**). Có thể giữ sẵn bộ biến trong file
`.env.render` ở gốc repo — `.gitignore` đã chặn mọi file `.env`, `.env.*`, `*.env` — rồi dùng
*Environment → Add from .env* để dán một lần:

| Tên | Giá trị |
|---|---|
| `ASPNETCORE_ENVIRONMENT` | `Production` (tắt Swagger) |
| `PORT` | `8080` (cổng image nghe) |
| `MongoSettings__ConnectionString` | chuỗi Atlas ở bước 1.4 |
| `MongoSettings__DatabaseName` | `newsdb` |
| `RedisSettings__ConnectionString` | chuỗi ở bước 2.3 |
| `SessionSettings__TtlMinutes` | `30` |
| `PostingSettings__AdminOnly` | `true` — **nên đặt**: chỉ admin đăng bài và tải ảnh, người khác vẫn đăng ký/đăng nhập/đọc bài được. Demo trên máy không đặt biến này nên không bị ảnh hưởng |
| `CloudinarySettings__CloudName`, `__ApiKey`, `__ApiSecret` | tùy chọn — thiếu thì upload ảnh trả 503 rõ ràng, phần còn lại vẫn chạy |

Deploy xong, mở `https://newscachesession-api.onrender.com/health` phải thấy `"status": "Healthy"` cho cả `mongodb` và `redis`.

> Deploy treo khoảng 15 phút rồi log báo `==> Timed Out` dù app đã chạy: Render không nhận được 200 từ health
> check. Lần deploy đầu bị đúng lỗi này vì ô **Health Check Path** gõ nhầm `/heath` → app trả 404. Kiểm tra
> *Settings → Health Checks* phải là `/health` (có `/`, không khoảng trắng), sửa xong bấm *Manual Deploy*.
> Log khởi động phải ghi `Now listening on: http://0.0.0.0:8080` — Render yêu cầu bind `0.0.0.0`, `Dockerfile`
> đã đặt sẵn `ASPNETCORE_URLS`.

> Nếu tên `newscachesession-api` đã có người dùng và Render cấp URL khác (thêm hậu tố), sửa **2 dòng
> `destination`** trong `src/frontend/vercel.json` cho đúng URL thật, commit lên `main` rồi mới làm bước 6.

## 4. Đăng ký admin NGAY

Atlas không có `users` nên **người đăng ký đầu tiên thành admin**. Làm ngay sau khi Render lên, trước khi
gửi URL cho bất kỳ ai:

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"username":"<tên-admin>","password":"<mật-khẩu-mạnh>"}' \
  https://newscachesession-api.onrender.com/api/auth/register
# phải thấy "role":"admin"
```

Người đến sau là user thường. Muốn cấp thêm admin: `db.users.updateOne({username: "..."}, {$set: {role: "admin"}})`
trong Atlas Data Explorer. Reset dữ liệu thì drop cả `users` lẫn `meta`.

## 5. Smoke test vào Render

```bash
export SMOKE_ADMIN_PASS='<mật-khẩu-admin>'
python scripts/Smoke/smoke_test.py --base-url https://newscachesession-api.onrender.com --admin-user <tên-admin>
```

8 bước phải `PASS` (script tự tạo rồi tự xóa một bài test). Lần đầu có thể chậm ~1 phút nếu server đang ngủ.

## 6. Vercel (frontend)

1. *Add New → Project* → chọn repo → **Root Directory: `src/frontend`**, Framework: Vite,
   Build: `npm run build`, Output: `dist`.
2. File `src/frontend/vercel.json` đã có sẵn trong repo (URL Render theo tên ở bước 3):

   ```json
   {
     "$schema": "https://openapi.vercel.sh/vercel.json",
     "rewrites": [
       { "source": "/api/:path*", "destination": "https://newscachesession-api.onrender.com/api/:path*" },
       { "source": "/health", "destination": "https://newscachesession-api.onrender.com/health" },
       { "source": "/(.*)", "destination": "/index.html" }
     ],
     "headers": [
       {
         "source": "/api/(.*)",
         "headers": [
           { "key": "Cache-Control", "value": "no-store" },
           { "key": "CDN-Cache-Control", "value": "no-store" }
         ]
       }
     ]
   }
   ```

   Thứ tự rewrite quan trọng: `/api` phải đứng trước luật bắt-tất-cả `/(.*)`. Header `no-store` chặn CDN
   giữ response `/api` — nếu không, `X-Cache` và nội dung bài có thể bị Vercel trả bản cũ.

## 7. Smoke test qua Vercel

```bash
python scripts/Smoke/smoke_test.py --base-url https://<app>.vercel.app --admin-user <tên-admin> \
  --spa-url https://<app>.vercel.app
```

9 bước: thêm F5 ở `/posts/{id}` (phải 200 HTML) và kiểm tra `x-vercel-cache` không phải `HIT` trên `/api`.
Sau đó mở trình duyệt: badge HIT/MISS ở trang chi tiết, đăng nhập admin, trang *Quản lý phiên*.

## 8. Đo cold start

Để server không có request hơn 15 phút rồi:

```bash
curl -s -o /dev/null -w 'cold start: %{time_total}s\n' https://newscachesession-api.onrender.com/health
```

| Ngày | Thời gian thức dậy | Gọi lại ngay sau đó |
|---|---|---|
| 26/10/2026 (sau 17 phút không có request) | **33,6 s** | 0,22 s |

## Bản quyền, Google và cờ "trang không an toàn"

| Rủi ro | Đã làm | Bạn cần giữ |
|---|---|---|
| Bản quyền nội dung | Bản deploy chỉ có bài Wikipedia (CC BY-SA) và Wikinews (CC BY); **mỗi bài** có khối "Ghi nguồn": link bài gốc, giấy phép, nguồn và tác giả ảnh. Footer ghi giấy phép, không tuyên bố "bảo lưu" nội dung. Bỏ 150 bài VnExpress | Không chép thêm bài/ảnh từ báo hay trang có bản quyền; không xóa khối "Ghi nguồn" |
| Google coi là trang chép nội dung (spam) | `noindex, nofollow` bằng thẻ meta trong `index.html` và header `X-Robots-Tag` trên mọi đường dẫn Vercel → Google không đưa trang vào kết quả tìm kiếm | **Không** thêm `Disallow: /` vào `robots.txt`: chặn crawl thì Google không đọc được `noindex`, URL vẫn có thể hiện trong kết quả |
| Bị Safe Browsing gắn cờ "trang lừa đảo" | HTTPS, cookie `Secure` + `HttpOnly`, không render HTML do người dùng nhập (chỉ chuyển URL thành link), chuyển hướng sau đăng nhập chỉ trong cùng trang, không có ảnh `http://`, tên và giao diện không nhái báo nào | Không dùng logo/tên báo thật, không đổi tên miền sang tên giống thương hiệu khác |
| Người lạ đăng link lừa đảo (link trong bài hiện thành link bấm được) | `PostingSettings__AdminOnly=true` trên Render: chỉ admin đăng bài / tải ảnh, người khác nhận 403 "Bản demo trực tuyến chỉ cho quản trị viên đăng bài và tải ảnh." | Giữ biến này trên Render; không chia sẻ tài khoản admin |

Kiểm tra định kỳ:
- Trạng thái Safe Browsing: <https://transparencyreport.google.com/safe-browsing/search> (dán URL Vercel).
- Thêm URL Vercel vào **Google Search Console** → mục *Security issues* sẽ báo ngay nếu trang bị gắn cờ, và
  là nơi gửi yêu cầu xem xét lại sau khi gỡ nội dung xấu.
- Vào *Quản trị bài viết* xem có bài lạ không; có thì xóa và thu hồi phiên của tài khoản đó.
- Chấm xong thì gỡ deploy (mục dưới) — trang không người trông là trang dễ bị lợi dụng nhất.

## Rollback và gỡ bỏ

- Render: *Events* → chọn deploy trước → **Rollback**. Vercel: *Deployments* → **Instant Rollback**.
- Dữ liệu Atlas: chạy lại bước 1.5 với `mongorestore --drop`.
- Gỡ hẳn: xóa service Render, project Vercel, cluster Atlas, database Redis Cloud.

## Bảo mật

- Chuỗi kết nối, mật khẩu chỉ nằm trong dashboard Render/Vercel và biến môi trường máy cá nhân —
  tài liệu này chỉ ghi **tên** biến.
- Atlas mở `0.0.0.0/0` → bắt buộc mật khẩu DB mạnh, user chỉ có `readWrite` trên `newsdb`.
- Ai cũng đăng ký được tài khoản thường và đăng bài — chấp nhận cho đồ án.
- Render kết thúc HTTPS ở proxy rồi chuyển vào container bằng HTTP; API đọc `X-Forwarded-Proto`
  (`UseForwardedHeaders` trong `Program.cs`) nên cookie `SessionId` vẫn có cờ `Secure` trên bản deploy.
  Kiểm tra: DevTools → Application → Cookies, cột *Secure* phải được tích.
