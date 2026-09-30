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

## Cách chạy

```bash
# 1. Khởi động DB & Cache: MongoDB (27017), Redis (6379), RedisInsight (5540)
docker compose up -d

# 2. Chạy Backend API (Swagger: http://localhost:5134/swagger)
cd src/NewsCacheSession.Api && dotnet run

# 3. Chạy Frontend (UI: http://localhost:3000)
cd src/frontend && npm run dev
```

## Cấu trúc thư mục
- `src/NewsCacheSession.Api/` — project API chính
- `scripts/SeedPosts/` — seed 100 bài viết mẫu
- `scripts/Benchmark/` — đo hiệu năng DB vs Cache
- `docs/` — báo cáo

## Tài liệu
- [`AGENTS.md`](AGENTS.md) — hợp đồng dữ liệu + phân công file (đọc trước khi code)
- [`docs/mongodb-schema.md`](docs/mongodb-schema.md) — schema MongoDB, quy ước field, index
- [`docs/redis-keyspace.md`](docs/redis-keyspace.md) — keyspace Redis, TTL, luồng Cache-Aside
- [`docs/chot-thiet-ke-sv1.md`](docs/chot-thiet-ke-sv1.md) — các quyết định thiết kế đã chốt
- [`docs/nosql-jira-tasks.csv`](docs/nosql-jira-tasks.csv) — danh sách task theo sprint

## Phân công
| Thành viên | Vai trò | Phụ trách |
|---|---|---|
| Hồ Ngọc Phương Như | SV1 — Data Architect & CRUD Lead | Thiết kế DB gốc + mô hình dữ liệu Redis; API CRUD bài viết, đăng ký/đăng nhập |
| Nguyễn Anh Quan | SV2 — Advanced Query Specialist | Middleware Cache-Aside, TTL/EXPIRE, Cache Invalidation, bộ đếm INCR |
| Nguyễn Xuân Định | SV3 — Fullstack Integrator & DB Tester | Nạp 100 bài viết, đo hiệu năng, web tin tức, điều phối demo |