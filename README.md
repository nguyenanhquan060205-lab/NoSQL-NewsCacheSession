# NewsCacheSession — Đề tài 06: Caching bài viết & Session Management

Trang tin tức tích hợp Redis để cache bài viết và quản lý phiên đăng nhập.

## Stack
- ASP.NET Core 8 (Web API, Controllers)
- MongoDB — DB gốc (bài viết, tài khoản)
- Redis (StackExchange.Redis) — Cache-Aside + Session (Hash, TTL, INCR)

## Cách chạy
```bash
cd src/NewsCacheSession.Api
dotnet run
```

Yêu cầu: MongoDB và Redis đang chạy local (mặc định `localhost:27017` và `localhost:6379`).

## Cấu trúc thư mục
- `src/NewsCacheSession.Api/` — project API chính
- `scripts/SeedPosts/` — seed 100 bài viết mẫu
- `scripts/Benchmark/` — đo hiệu năng DB vs Cache
- `docs/` — báo cáo

## Phân công
| Thành viên | Vai trò |
|---|---|
| Quan | Data Architect & CRUD Lead |
| ??? | Advanced Query Specialist (Cache-Aside, TTL, Invalidation, INCR) |
| ??? | Fullstack Integrator & DB Tester |