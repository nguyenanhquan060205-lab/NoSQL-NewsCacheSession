# Quá Trình Dựng Khung — ĐỀ TÀI 06

## Giai đoạn 1: Khởi tạo project 
- Tạo ASP.NET Core 8 Web API
- Cài NuGet: MongoDB.Driver, StackExchange.Redis, Swashbuckle
- Cấu hình `appsettings.json` (MongoDB localhost:27017, Redis localhost:6379)

## Giai đoạn 2: Models & Data Layer 
- `Models/Post.cs` — BsonId, Title, Content, ImageUrl, AuthorId, Views, Timestamps
- `Models/User.cs` — BsonId, Username, PasswordHash, CreatedAt
- `Data/MongoContext.cs` — MongoSettings + IMongoCollection<Post>, IMongoCollection<User>

## Giai đoạn 3: Redis Services 
- `Services/ICacheService.cs` — Get, Set, Remove, Increment
- `Services/RedisCacheService.cs` — StringGet/Set/Delete/Increment
- `Services/ISessionService.cs` — Create, Get, Refresh, Remove Session
- `Services/RedisSessionService.cs` — Hashes (HashSet/HashGetAll) + TTL (KeyExpire)

## Giai đoạn 4: DTOs 
- `DTOs/Auth/` — RegisterRequest, LoginRequest, LoginResponse, SessionInfoResponse
- `DTOs/Posts/` — CreatePostRequest, UpdatePostRequest, PostResponse

## Giai đoạn 5: Controllers 
- `Controllers/AuthController.cs` — Register, Login, Logout, Me (4 endpoints)
- `Controllers/PostsController.cs` — GetAll, GetById (Cache-Aside), Create, Update, Delete, IncrementView (6 endpoints)

## Giai đoạn 6: Middleware 
- `Middleware/SessionAuthMiddleware.cs` — Đọc SessionId từ Cookie → Redis → gán HttpContext.Items

## Giai đoạn 7: Program.cs 
- Thêm CORS policy
- Đăng ký SessionAuthMiddleware: `app.UseSessionAuth()`

## Giai đoạn 8: Scripts 
- `scripts/SeedPosts/seed.py` — Hướng dẫn nạp 100 bài viết (Faker + pymongo)
- `scripts/Benchmark/benchmark.py` — Hướng dẫn đo DB vs Cache (requests + matplotlib)

## Giai đoạn 9: Frontend (React + Vite + TailwindCSS)
- `src/frontend/` — React (Vite), TailwindCSS v4, React Router, Axios
- `src/frontend/src/services/api.js` — Axios client (proxy `/api` → backend)
- `src/frontend/src/components/Navbar.jsx` — Thanh điều hướng
- `src/frontend/src/components/PostCard.jsx` — Card hiển thị bài viết
- `src/frontend/src/pages/HomePage.jsx` — Trang chủ (danh sách bài viết)
- `src/frontend/src/pages/LoginPage.jsx` — Đăng nhập / Đăng ký
- `src/frontend/src/pages/PostDetailPage.jsx` — Chi tiết bài viết (demo Cache-Aside)
- `src/frontend/src/pages/CreateEditPostPage.jsx` — Tạo / Sửa bài viết

---

## Trạng thái hiện tại: BUILD SUCCEEDED (Backend 0 errors + Frontend 0 errors)

## Phân công implement (theo đề tài)

| TODO | Người phụ trách | File |
|---|---|---|
| AuthController (Register, Login, Logout, Me) | SV1 | Controllers/AuthController.cs |
| PostsController CRUD (GetAll, Create, Delete) | SV1 | Controllers/PostsController.cs |
| Cache-Aside (GetById), Cache Invalidation (Update) | SV2 | Controllers/PostsController.cs |
| INCR view count | SV2 | Controllers/PostsController.cs |
| SessionAuthMiddleware | SV2 | Middleware/SessionAuthMiddleware.cs |
| Frontend UI (HomePage, LoginPage, PostDetailPage, ...) | SV3 | src/frontend/src/pages/*.jsx |
| Seed 100 bài viết | SV3 | scripts/SeedPosts/seed.py |
| Benchmark DB vs Cache | SV3 | scripts/Benchmark/benchmark.py |

> Xem hướng dẫn chi tiết: `docs/huong_dan_nhom.md`

