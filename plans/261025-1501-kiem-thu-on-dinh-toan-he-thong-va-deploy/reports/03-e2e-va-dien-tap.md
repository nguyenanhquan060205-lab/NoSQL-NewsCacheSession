# Phase 3 — E2E giao diện, script SV3 và diễn tập demo (26/10/2026)

## Phần A — E2E trên stack QA (Vite `:3001` → API `:5135`)

Chạy bằng Playwright (`playwright-core` 1.62.1 + Chromium 1243 có sẵn trên máy, không cài thêm), trình
duyệt headless 1280×900, API QA build từ `develop` **đã có bản sửa S1–S5** (`cd71517`). Script và ảnh
chụp nằm trong scratchpad, không commit.

| Mức | Người | Kịch bản | Kết quả |
|---|---|---|---|
| Critical | Định | Trang chủ: danh sách, phân trang, lọc chuyên mục | ✅ trang 2 OK; lọc "Công nghệ" → URL có `categoryId`; 0 lỗi JavaScript |
| Critical | Định+Quân | Mở chi tiết 2 lần | ✅ `CACHE MISS · Phản hồi GET: 8,1 ms` → `CACHE HIT · 5,2 ms`; header `X-Cache` khớp badge |
| High | Quân | Lượt xem trên trang chi tiết | ✅ `post:{id}:views` 7 → 8, trang hiện "8 lượt xem" |
| Critical | Định | Đăng ký, đăng nhập, sai mật khẩu, đăng xuất | ✅ "Tài khoản đã tạo. Đăng nhập để tiếp tục." · "Sai username hoặc password" · Navbar đổi trạng thái |
| Critical | Như | Admin tạo bài (có chuyên mục) → sửa → xóa | ✅ bài mới đứng đầu trang chủ; sửa xong mở lại MISS + tiêu đề mới; xóa → "Bài viết không tồn tại hoặc đã bị xóa." |
| High | Như | User thường sửa bài seed | ✅ "Bạn không có quyền sửa bài viết này.", tiêu đề giữ nguyên |
| High | Định | `/admin/posts`, `/admin/sessions` với user thường | ✅ cả hai hiện "Bạn không có quyền truy cập" |
| High | Định+Quân | Quản lý phiên: TTL đếm lùi, thu hồi phiên tab khác | ✅ "29 phút 59 giây" → "29 phút 57 giây"; tab bị thu hồi gửi request kế tiếp → về `/login` |
| Medium | Định | Upload ảnh khi chưa cấu hình Cloudinary | ✅ HTTP 503 "Cloudinary chưa được cấu hình.", form giữ dữ liệu |
| Medium | Định | F5 trực tiếp ở `/posts/{id}` và `/admin/posts` | ✅ cả hai hiển thị đúng |
| Medium | Định | Dừng API `:5135`, tải lại trang chủ (G20) | ✅ banner vàng ngay đầu nội dung: "**Chế độ xem trước giao diện.** Không kết nối được API nên các bài dưới đây là dữ liệu minh hoạ…" |
| Medium | Định | Khung 375px | ✅ `scrollWidth` 375 / 375 / 375 (trang chủ, chi tiết, đăng nhập) |

Ghi chú:
- Lần chạy đầu có 2 dòng FAIL do chính script (đếm heading trước khi `RequireAdmin` kiểm tra quyền xong;
  coi dòng log mạng `401` của `/api/auth/me` khi khách chưa đăng nhập là lỗi). Sửa script, chạy lại: 12/12.
- Trình duyệt in 4 dòng "Failed to load resource … 401" khi khách chưa đăng nhập — đó là `/api/auth/me`
  trả 401 đúng hợp đồng, không phải lỗi JavaScript.

**Kết luận G20: banner đủ rõ** (nằm trên cùng, nói thẳng "Không kết nối được API", thanh chuyên mục cũng
biến mất) → theo plan **không sửa D2**. Lưu ý khi demo: nếu thấy banner vàng là API đã chết.

## Phần B — Script của SV3 (venv)

| Việc | Kết quả |
|---|---|
| `seed.py` chạy lần 2 trên `newsdb_qa` | ✅ "0 mới, 100 đã tồn tại" — không nhân đôi (Phase 1) |
| `seed.py --count 50` | ✅ bị chặn: "SCRUM-32 yêu cầu tối thiểu 100 bài" |
| `pytest` SeedPosts / SeedRedis / Benchmark | ✅ 17 / 33 / 14 pass (G5 là lỗi môi trường — xem `01-baseline.md`) |
| `benchmark.py` bản ngắn trỏ QA (`--redis redis://localhost:6380/0`, `--out` vào scratchpad) | ✅ xem bên dưới |
| `plot.py <thư mục kết quả>` | ✅ "Đã vẽ 5 biểu đồ … và ghi summary.md" |

Benchmark QA (API đã có bản sửa):
```
cache-miss  n=10  median 2.57 ms      cache-hit  n=10  median 0.87 ms
Mẫu không hợp lệ (sai X-Cache / lỗi HTTP): 0       MISS/HIT = 2.96 lần
S2 stampede: MISS = 1/50, lỗi = 0, p95 = 62.58 ms
S3: cache-hit c=10 3794 req/s p95 3.42 ms · khong-cache c=10 3177 req/s p95 4.93 ms · lỗi = 0
```
Redis demo `DBSIZE` trước/sau: 0 / 0 — không bị đụng. Repo không có file mới (kết quả ghi ra scratchpad
thay vì `results/qa-kiem-thu/`, khỏi phải xóa).

Lỗi nhỏ (báo Định, không chặn gì): `plot.py --help` không in hướng dẫn mà coi `--help` là đường dẫn →
`FileNotFoundError: '--help/raw_latency.csv'`.

## Phần C — Chuẩn bị stack demo và diễn tập

| Bước | Trạng thái |
|---|---|
| C1. Sao lưu `newsdb` | ✅ `mongodump --gzip` → 44 MB trong scratchpad, `mongorestore --dryRun` đọc được. Trước sao lưu: 10 251 bài (10 150 chưa xóa), 3 user (2 admin), 7 chuyên mục |
| C2. Trả cổng 27017 cho container | ✅ (Quân đồng ý 26/10) `brew services stop mongodb-community` → `docker compose up -d --force-recreate mongo`: `0.0.0.0:27017->27017`, cùng volume `nosql-newscachesession_mongo_data`, vẫn 10 251 bài (10 150 chưa xóa), 3 user, 7 chuyên mục. Cổng 27018 trước đó đến từ file override `mongo-port-override.yml` của một phiên làm việc cũ |
| C3. Dừng API demo PID 59923, chạy lại từ `develop` | ✅ Dừng PID 59923 (chạy từ 23/10 14:37). Chạy lại bằng đúng lệnh README `dotnet run --project src/NewsCacheSession.Api`, **không** biến môi trường `MongoSettings__*` (kiểm `ps eww`: 0) → `/health` Healthy, `totalItems` 10 150. Vite `:3000` (PID 55807) proxy sang API mới trả 200. **README chạy đúng như viết** (G1, G2 xong) |
| C4. Seed Redis demo 20–50 key | ✅ `seed_redis.py --demo-username demo_user --dry-run` → `{"ok": true, "total": 40, "sessions": 20, "caches": 20, "writes": 0}`; chạy thật → `live: 40, missingOrInvalid: 0`; `verify_seed_redis.py` → `ok: true`. `DBSIZE` = 41 (20 Hash `session:*`, 20 String `post:*`, 1 cache danh sách), **22 giá trị TTL khác nhau** (G3, G4 xong) |
| C5. Diễn tập 3 bước × 2 lượt | ✅ tự động (bảng dưới) |

### Diễn tập tự động (Playwright trên Vite `:3000` + lệnh đọc Redis demo)

Bước 2 dùng một phiên `demo_user` có sẵn trong manifest seed để tạo bài tạm, sửa, xóa; xong thì xóa hẳn
2 bài tạm khỏi MongoDB theo đúng `_id` → dữ liệu demo về lại 10 251 / 10 150 bài.

| Lượt | Bước 1 — MISS rồi HIT (trình duyệt) | Bước 2 — sửa bài xóa cache | Bước 3 — TTL phiên |
|---|---|---|---|
| 1 | `MISS · 19,1 ms` → `HIT · 9,6 ms` (0,6 s) | `post:{id}` EXISTS 1 → **0** ngay sau PUT; `posts:ver` 1 → 2; GET kế tiếp MISS, tiêu đề mới (0,2 s) | `306 → 303` sau 3 s → **1800** sau 1 request (3,3 s) |
| 2 | `MISS · 13,9 ms` → `HIT · 4,9 ms` (0,4 s) | EXISTS 1 → **0**; `posts:ver` 4 → 5; GET MISS, tiêu đề mới (0,1 s) | `459 → 456` → **1800** (3,5 s) |

Sau diễn tập Redis demo có 49 key — mỗi bài được mở thêm một key `post:{id}` (TTL 10 phút), nên số key tăng
dần khi duyệt web. **Seed lại ngay trước buổi chấm** (phiên seed sống tối đa 30 phút) để đúng khoảng 20–50.

Còn lại cho người: diễn tập có thuyết trình trên RedisInsight và quay video dự phòng là SCRUM-45 của Định.
