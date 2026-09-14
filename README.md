# NewsCacheSession — Đề tài 06: Caching bài viết & Session Management

Trang tin tức tích hợp Redis để cache bài viết và quản lý phiên đăng nhập.

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

## Phân công
| Thành viên | Vai trò |
|---|---|
|  | Data Architect & CRUD Lead |
|  | Advanced Query Specialist (Cache-Aside, TTL, Invalidation, INCR) |
|  | Fullstack Integrator & DB Tester |