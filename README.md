# NewsCacheSession — Đề tài 06: Caching bài viết & Session Management

Trang tin tức tích hợp Redis để cache bài viết và quản lý phiên đăng nhập.

> 📌 **Trước khi viết code — kể cả khi dùng AI (Claude Code, Copilot, Cursor…) — hãy đọc
> [`AGENTS.md`](AGENTS.md).** File đó là hợp đồng dữ liệu chung của nhóm: quy ước đặt tên
> field MongoDB, keyspace Redis, bảng phân công file và những việc còn thiếu. Làm sai quy
> ước trong đó là hỏng dữ liệu hoặc hỏng kịch bản demo.

## Stack
- ASP.NET Core 8 (Web API, Controllers)
- MongoDB — DB gốc (bài viết, tài khoản)
- Redis (StackExchange.Redis) — Cache-Aside + Session (Hash, TTL, INCR)
- React 19 + Vite + Tailwind 4 (frontend)

## Yêu cầu cài đặt

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| .NET SDK | **8.0+** (chạy test cần **10**) | chạy API; project test nhắm `net10.0` |
| Node.js | 20+ | chạy frontend |
| Docker Desktop | bản mới | MongoDB, Redis, RedisInsight |
| Python | 3.10+ | script seed dữ liệu |

> ⚠️ **Máy đã cài sẵn MongoDB như một service của Windows?** Nó chiếm cổng 27017 và API
> sẽ nối vào bản đó thay vì container, khiến Docker volume không được dùng và `mongosh`
> trong container soi ra DB rỗng. Dừng nó trước (PowerShell **quyền admin**):
>
> ```powershell
> net stop MongoDB
> Set-Service MongoDB -StartupType Manual   # không tự bật lại sau khi khởi động máy
> ```
>
> **macOS cài MongoDB qua Homebrew** cũng chiếm `127.0.0.1:27017` (kiểm tra:
> `lsof -nP -iTCP:27017 -sTCP:LISTEN` thấy `mongod` thay vì `com.docker…`). Dừng trước khi
> `docker compose up`: `brew services stop mongodb-community` (bật lại khi cần dùng project khác).

## Cách chạy

Chạy **tất cả các lệnh dưới đây từ thư mục gốc của repo**, trừ bước 7 có ghi chú riêng.

```bash
# 1. Hạ tầng: MongoDB (27017), Redis (6379), RedisInsight (5540)
docker compose up -d

# 2. Backend API — Swagger: http://localhost:5134/swagger
dotnet run --project src/NewsCacheSession.Api --urls http://localhost:5134

# 3. Kiểm tra sức khỏe TRƯỚC KHI đi tiếp — phải thấy "status":"Healthy" cho cả hai
curl http://localhost:5134/health
```

```bash
# 4. Seed tối thiểu 100 bài viết có ảnh vào MongoDB (luôn thử --dry-run trước)
python -m pip install -r scripts/SeedPosts/requirements.txt
python scripts/SeedPosts/seed.py --dry-run
python scripts/SeedPosts/seed.py

# 5. Tạo tài khoản qua Swagger hoặc POST /api/auth/register
#    ⚠️ NGƯỜI ĐĂNG KÝ ĐẦU TIÊN TỰ ĐỘNG LÀ ADMIN — không có admin cài sẵn.
#    Đăng ký thêm một tài khoản thường (role=user) để dùng cho bước 6.

# 6. Seed 20–50 session/cache key với TTL khác nhau (cần API ở bước 2 đang chạy)
python -m pip install -r scripts/SeedRedis/requirements.txt
python scripts/SeedRedis/seed_redis.py --demo-username <tên-tài-khoản-role-user> --dry-run
python scripts/SeedRedis/seed_redis.py --demo-username <tên-tài-khoản-role-user>
```

```bash
# 7. Frontend — UI: http://localhost:3000 (mở MỘT CỬA SỔ TERMINAL RIÊNG)
cd src/frontend
npm install        # lần đầu, hoặc sau khi package.json đổi
npm run dev
```

Bài seed có `authorId = null` nên **chỉ admin sửa/xóa được** — bị 403 ở đây là đúng
thiết kế, không phải lỗi.

## Test

```bash
# Backend — unit test dùng mock, không cần Redis/Mongo; integration test tự bỏ qua (Skipped)
dotnet test

# Frontend
cd src/frontend && npm test
```

**Integration test** đi qua HTTP thật tới Redis + MongoDB thật (đăng ký/đăng nhập, CRUD, Cache-Aside,
invalidation, session, lượt xem, Redis/Mongo sập). Chạy trên container **riêng**, không đụng dữ liệu demo:

```bash
docker run -d --name news-mongo-qa -p 27019:27017 mongo:7.0
docker run -d --name news-redis-qa -p 6380:6379 redis:7-alpine redis-server --save "" --appendonly no
NEWS_IT=1 dotnet test
```

Test chỉ dùng database `newsdb_it_*` (tự xóa khi xong) và Redis DB 15 (`FLUSHDB` trước mỗi test).
Trỏ sang chỗ khác bằng `NEWS_IT_MONGO` / `NEWS_IT_REDIS`. Dọn: `docker rm -f news-mongo-qa news-redis-qa`.

**Smoke test** sau khi chạy hoặc deploy (tự tạo rồi tự xóa một bài test, cần tài khoản admin):

```bash
SMOKE_ADMIN_PASS=... python scripts/Smoke/smoke_test.py --base-url http://localhost:5134 --admin-user <admin>
```

> ⚠️ `tests/NewsCacheSession.Tests.csproj` đang nhắm `net10.0` còn API nhắm `net8.0`.
> Máy chỉ có SDK 9 sẽ **fail ngay lúc build** (`NETSDK1045`) — đây là lệch
> TargetFramework, **không phải lỗi code**. Build riêng API vẫn chạy được:
> `dotnet build src/NewsCacheSession.Api/NewsCacheSession.Api.csproj`.

## Cấu trúc thư mục
- `src/NewsCacheSession.Api/` — project API chính
- `src/frontend/` — giao diện React + Vite
- `scripts/SeedPosts/` — seed 100 bài viết mẫu
- `scripts/SeedRedis/` — seed session + cache key có TTL khác nhau
- `scripts/Benchmark/` — đo hiệu năng DB vs Cache
- `tests/` — test tự động backend (xUnit)
- `docs/` — báo cáo và tài liệu thiết kế

## Tài liệu
- [`AGENTS.md`](AGENTS.md) — hợp đồng dữ liệu + phân công file (đọc trước khi code)
- [`docs/mongodb-schema.md`](docs/mongodb-schema.md) — schema MongoDB, quy ước field, index
- [`docs/redis-keyspace.md`](docs/redis-keyspace.md) — keyspace Redis, TTL, luồng Cache-Aside
- [`docs/chot-thiet-ke-sv1.md`](docs/chot-thiet-ke-sv1.md) — các quyết định thiết kế đã chốt
- [`docs/bao-cao-nguyen-ly-cache-aside.md`](docs/bao-cao-nguyen-ly-cache-aside.md) — báo cáo nguyên lý Cache-Aside
- [`docs/checklist-barem.md`](docs/checklist-barem.md) — đối chiếu barem 10 điểm, bằng chứng và chỗ còn thiếu
- [`docs/ra-soat-cai-dat-tu-dau.md`](docs/ra-soat-cai-dat-tu-dau.md) — nhật ký cài đặt từ máy sạch và kết quả kiểm chứng
- [`docs/nosql-jira-tasks.csv`](docs/nosql-jira-tasks.csv) — danh sách task theo sprint

## Phân công
| Thành viên | Vai trò | Phụ trách |
|---|---|---|
| Hồ Ngọc Phương Như | SV1 — Data Architect & CRUD Lead | Thiết kế DB gốc + mô hình dữ liệu Redis; API CRUD bài viết, đăng ký/đăng nhập |
| Nguyễn Anh Quân | SV2 — Advanced Query Specialist | Middleware Cache-Aside, TTL/EXPIRE, Cache Invalidation, bộ đếm INCR |
| Nguyễn Xuân Định | SV3 — Fullstack Integrator & DB Tester | Nạp 100 bài viết, đo hiệu năng, web tin tức, điều phối demo |
