# 📖 Hướng Dẫn Đầy Đủ Cho Nhóm — ĐỀ TÀI 06

> **Phân hệ Caching Bài Viết & Quản Lý Phiên (Session Management)**
>
> Tài liệu này giải thích **toàn bộ kiến trúc, cách cài đặt, cách chạy, luồng hoạt động, và hướng dẫn implement chi tiết** cho từng thành viên. Đọc từ đầu đến cuối để nắm rõ trước khi bắt tay vào code.

---

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Cài đặt môi trường](#2-cài-đặt-môi-trường)
3. [Cấu hình Database (MongoDB + Redis)](#3-cấu-hình-database-mongodb--redis)
4. [Cấu hình & chạy Backend](#4-cấu-hình--chạy-backend)
5. [Cấu hình & chạy Frontend](#5-cấu-hình--chạy-frontend)
6. [Giải thích cấu trúc project](#6-giải-thích-cấu-trúc-project)
7. [Luồng hoạt động chính](#7-luồng-hoạt-động-chính)
8. [Thiết kế dữ liệu trên Redis](#8-thiết-kế-dữ-liệu-trên-redis)
9. [Hướng dẫn SV1 — Data Architect & CRUD Lead](#9-hướng-dẫn-sv1--data-architect--crud-lead)
10. [Hướng dẫn SV2 — Advanced Query Specialist](#10-hướng-dẫn-sv2--advanced-query-specialist)
11. [Hướng dẫn SV3 — Fullstack Integrator & DB Tester](#11-hướng-dẫn-sv3--fullstack-integrator--db-tester)
12. [Kịch bản Demo Bảo Vệ](#12-kịch-bản-demo-bảo-vệ)
13. [Lỗi thường gặp & Cách sửa](#13-lỗi-thường-gặp--cách-sửa)

---

## 1. Tổng quan kiến trúc

```
┌──────────────────────────────────────────────────────────────┐
│                        NGƯỜI DÙNG                            │
│                     (Trình duyệt web)                        │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP Request
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              FRONTEND — React + Vite + TailwindCSS           │
│                     http://localhost:3000                     │
│                                                              │
│  Pages: HomePage, LoginPage, PostDetailPage, CreateEditPage  │
│  Gọi API qua axios → proxy /api/* → Backend                 │
└────────────────────────┬─────────────────────────────────────┘
                         │ /api/*  (Vite proxy)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              BACKEND — ASP.NET Core 8 Web API                │
│                     http://localhost:5134                     │
│                                                              │
│  Pipeline: CORS → SessionAuthMiddleware → Authorization      │
│                                                              │
│  Controllers:                                                │
│    AuthController   → /api/auth/*   (register/login/logout)  │
│    PostsController  → /api/posts/*  (CRUD + Cache-Aside)     │
│                                                              │
│  Services:                                                   │
│    ICacheService → RedisCacheService   (Strings, INCR)       │
│    ISessionService → RedisSessionService (Hashes, TTL)       │
└─────────────┬────────────────────────────┬───────────────────┘
              │                            │
              ▼                            ▼
┌─────────────────────────┐  ┌─────────────────────────────────┐
│    MongoDB (DB gốc)     │  │       Redis (Cache + Session)    │
│   localhost:27017       │  │       localhost:6379              │
│                         │  │                                   │
│  Database: newsdb       │  │  Strings:  post:{id}    (cache)   │
│  Collections:           │  │  Strings:  post_views:{id} (INCR)│
│    - posts (100 bài)    │  │  Hashes:   session:{id} (session)│
│    - users              │  │            ↳ userId, username,    │
│                         │  │              loginAt + TTL 30min  │
└─────────────────────────┘  └─────────────────────────────────┘
```

**Tóm tắt**: Người dùng truy cập Frontend (React) → Frontend gọi Backend (API) → Backend đọc/ghi MongoDB (dữ liệu chính) và Redis (cache + session).

### Mô hình kiến trúc Backend — MVC + Service Layer

Backend sử dụng mô hình **MVC (Model-View-Controller)** — cụ thể là **MC (không có View)** vì đây là Web API, không render HTML:

```
┌─────────────────────────────────────────────────────────┐
│                    MVC + Service Layer                    │
│                                                          │
│  Controller        ← Nhận request, trả response (JSON)  │
│      ↓ dùng                                              │
│  DTO               ← Định dạng dữ liệu vào/ra API      │
│      ↓ khác với                                          │
│  Model             ← Mapping với document MongoDB        │
│      ↓ truy cập qua                                     │
│  Data Layer         ← MongoContext (Repository pattern)  │
│      ↓ và                                                │
│  Service Layer      ← ICacheService, ISessionService     │
│                       (tách logic Redis ra khỏi Controller)│
│      ↓ đăng ký qua                                      │
│  Dependency Injection (DI) ← Program.cs cấu hình        │
│      ↓ đi qua                                           │
│  Middleware Pipeline ← CORS → SessionAuth → Auth → Route│
└─────────────────────────────────────────────────────────┘
```

**Các pattern được áp dụng:**

| Pattern | Dùng ở đâu | Giải thích |
|---|---|---|
| **MVC** | Controllers + Models | Tách riêng tầng xử lý request (Controller) và tầng dữ liệu (Model) |
| **Service Layer** | `ICacheService`, `ISessionService` | Tách logic nghiệp vụ Redis ra khỏi Controller, dễ test và thay đổi |
| **Dependency Injection** | `Program.cs` | Controller không tự tạo service, .NET inject qua constructor |
| **Cache-Aside** | `PostsController.GetById()` | Kiểm tra cache trước → miss → đọc DB → ghi ngược cache + TTL |
| **Middleware Pipeline** | `SessionAuthMiddleware` | Xử lý xác thực session TRƯỚC khi request đến Controller |

### Mô hình kiến trúc Frontend — SPA + Component-Based

Frontend sử dụng mô hình **SPA (Single Page Application)** kết hợp **Component-Based Architecture** của React:

```
┌─────────────────────────────────────────────────────────┐
│              SPA + Component-Based Architecture           │
│                                                          │
│  main.jsx          ← Entry point, render <App />         │
│      ↓                                                   │
│  App.jsx           ← Router (BrowserRouter)              │
│      ↓ route tới                                         │
│  Pages/            ← Mỗi URL = 1 Page component         │
│      ↓ sử dụng                                           │
│  Components/       ← UI tái sử dụng (Navbar, PostCard)  │
│      ↓ gọi API qua                                       │
│  Services/api.js   ← Tập trung mọi HTTP call (axios)    │
│      ↓ proxy tới                                         │
│  Vite Dev Server   ← /api/* → http://localhost:5134      │
└─────────────────────────────────────────────────────────┘
```

**Các pattern được áp dụng:**

| Pattern | Dùng ở đâu | Giải thích |
|---|---|---|
| **SPA** | React + React Router | Chỉ load 1 file HTML duy nhất, chuyển trang bằng JS (không reload) |
| **Component-Based** | `Navbar.jsx`, `PostCard.jsx`, Pages | Mỗi phần UI là 1 component độc lập, có state riêng, tái sử dụng được |
| **Service Layer** | `services/api.js` | Tập trung tất cả API call vào 1 file, Pages không gọi axios trực tiếp |
| **Proxy Pattern** | `vite.config.js` | Frontend không biết Backend ở đâu, Vite proxy chuyển tiếp `/api/*` |

---

## 2. Cài đặt môi trường

### 2.1 Phần mềm cần cài

| Phần mềm | Version | Tải ở đâu | Dùng để làm gì |
|---|---|---|---|
| **.NET 8 SDK** | 8.0+ | [dotnet.microsoft.com/download](https://dotnet.microsoft.com/download) | Chạy Backend API |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) | Chạy Frontend React |
| **MongoDB Community** | 7.0+ | [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community) | Database gốc |
| **Redis** (Windows) | Bất kỳ | [github.com/microsoftarchive/redis/releases](https://github.com/microsoftarchive/redis/releases) hoặc dùng **Memurai** | Cache + Session |
| **MongoDB Compass** | Bất kỳ | [mongodb.com/products/compass](https://www.mongodb.com/products/compass) | GUI xem dữ liệu MongoDB |
| **Redis Insight** | Bất kỳ | [redis.io/insight](https://redis.io/insight/) | GUI xem dữ liệu Redis (quan trọng cho demo!) |
| **Python 3** | 3.9+ | [python.org](https://python.org) | Chạy script seed + benchmark |
| **Git** | Bất kỳ | [git-scm.com](https://git-scm.com) | Quản lý source code |

### 2.2 Kiểm tra đã cài đúng chưa

Mở terminal (PowerShell / CMD) chạy lần lượt:

```bash
# .NET
dotnet --version
# Kết quả mong đợi: 8.0.xxx

# Node.js
node --version
# Kết quả mong đợi: v18.x.x trở lên

npm --version
# Kết quả mong đợi: 9.x.x trở lên

# Python
python --version
# Kết quả mong đợi: Python 3.9+

# Git
git --version
```

---

## 3. Cấu hình Database (MongoDB + Redis)

### 3.1 MongoDB

#### Khởi động MongoDB
```bash
# Nếu cài MongoDB Community Server dạng service → tự chạy khi bật máy
# Nếu không, chạy thủ công:
mongod --dbpath "C:\data\db"
```

#### Kiểm tra kết nối
```bash
# Mở terminal mới:
mongosh
# Hoặc mở MongoDB Compass → kết nối: mongodb://localhost:27017
```

#### Thông tin kết nối (đã cấu hình trong project)
```
Connection String: mongodb://localhost:27017
Database Name:     newsdb
Collections:       posts, users
```

> Không cần tạo database hay collection thủ công — MongoDB sẽ **tự tạo** khi có dữ liệu đầu tiên được insert.

#### Cấu trúc dữ liệu MongoDB

**Collection `posts`**:
```json
{
  "_id": ObjectId("64a1b2c3d4e5f6..."),
  "Title": "Tiêu đề bài viết",
  "Content": "Nội dung chi tiết...",
  "ImageUrl": "https://picsum.photos/800/400",
  "AuthorId": "64a1b2c3d4e5f6...",
  "Views": 0,
  "CreatedAt": ISODate("2026-08-20T10:00:00Z"),
  "UpdatedAt": ISODate("2026-08-20T10:00:00Z")
}
```

**Collection `users`**:
```json
{
  "_id": ObjectId("64a1b2c3d4e5f6..."),
  "Username": "admin",
  "PasswordHash": "$2a$11$xxxx...",
  "CreatedAt": ISODate("2026-08-20T10:00:00Z")
}
```

### 3.2 Redis

#### Khởi động Redis
```bash
# Windows — nếu cài từ MSI:
redis-server

# Hoặc nếu cài dạng service → tự chạy khi bật máy
```

#### Kiểm tra kết nối
```bash
redis-cli ping
# Kết quả mong đợi: PONG
```

#### Thông tin kết nối (đã cấu hình trong project)
```
Connection String: localhost:6379
```

#### Các lệnh Redis hữu ích (cần biết cho demo)
```bash
# Xem tất cả key
redis-cli KEYS "*"

# Xem cache bài viết (kiểu String)
redis-cli GET "post:64a1b2c3d4e5f6"

# Xem TTL còn lại (giây)
redis-cli TTL "post:64a1b2c3d4e5f6"

# Xem session (kiểu Hash)
redis-cli HGETALL "session:abc-def-123"

# Xem lượt xem (kiểu String, giá trị số)
redis-cli GET "post_views:64a1b2c3d4e5f6"

# Xóa 1 key
redis-cli DEL "post:64a1b2c3d4e5f6"

# Xóa toàn bộ (CẨNTHẬN!)
redis-cli FLUSHALL
```

---

## 4. Cấu hình & chạy Backend

### 4.1 File cấu hình

**`src/NewsCacheSession.Api/appsettings.json`**:
```json
{
  "MongoSettings": {
    "ConnectionString": "mongodb://localhost:27017",
    "DatabaseName": "newsdb"
  },
  "RedisSettings": {
    "ConnectionString": "localhost:6379"
  }
}
```

> Nếu MongoDB/Redis chạy ở port khác, sửa ở đây.

**`src/NewsCacheSession.Api/Properties/launchSettings.json`**:
- Backend chạy ở **`http://localhost:5134`** (profile `http`)
- Swagger UI tự mở tại **`http://localhost:5134/swagger`**

### 4.2 Các NuGet package đã cài

| Package | Version | Dùng để |
|---|---|---|
| `MongoDB.Driver` | 3.11.0 | Kết nối + query MongoDB |
| `StackExchange.Redis` | 3.1.13 | Kết nối + thao tác Redis |
| `Swashbuckle.AspNetCore` | 6.6.2 | Swagger UI để test API |

> Nếu cần thêm BCrypt:
> ```bash
> cd src/NewsCacheSession.Api
> dotnet add package BCrypt.Net-Next
> ```

### 4.3 Chạy Backend

```bash
cd src/NewsCacheSession.Api
dotnet run
```

**Lần đầu** sẽ mất vài giây để restore packages. Khi thấy dòng:
```
Now listening on: http://localhost:5134
```
→ Backend đã sẵn sàng!

### 4.4 Test API bằng Swagger

Mở trình duyệt → `http://localhost:5134/swagger`

Swagger liệt kê tất cả endpoint. Click vào endpoint → "Try it out" → nhập dữ liệu → "Execute" → xem kết quả.

> **Lưu ý**: Hiện tại tất cả endpoint đều trả `500 NotImplementedException` vì chưa implement. Đó là bình thường — các bạn sẽ implement từng cái.

### 4.5 Pipeline Middleware (thứ tự quan trọng!)

Trong `Program.cs`, thứ tự middleware:
```
Request đi vào
    ↓
1. UseCors()              ← Cho phép frontend gọi API cross-origin
    ↓
2. UseSessionAuth()       ← Đọc Cookie → check Redis Session → gán HttpContext.Items
    ↓
3. UseAuthorization()     ← .NET authorization (mặc định)
    ↓
4. MapControllers()       ← Gọi đúng Controller theo route
    ↓
Response trả về
```

---

## 5. Cấu hình & chạy Frontend

### 5.1 Tech stack Frontend

| Thư viện | Version | Dùng để |
|---|---|---|
| `react` | 19.x | UI framework |
| `react-dom` | 19.x | Render React vào DOM |
| `react-router-dom` | 7.x | Routing (chuyển trang) |
| `axios` | 1.x | Gọi HTTP API |
| `tailwindcss` | 4.x | CSS utility classes |
| `vite` | 8.x | Build tool + dev server |

### 5.2 Cài dependencies

```bash
cd src/frontend
npm install
```

### 5.3 Chạy Frontend

```bash
npm run dev
```

Frontend chạy ở **`http://localhost:3000`**

### 5.4 Cách proxy hoạt động

Trong **`vite.config.js`**:
```javascript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:5134',  // Backend port
      changeOrigin: true,
    },
  },
}
```

**Nghĩa là**: Khi Frontend gọi `GET /api/posts`, Vite dev server sẽ tự động chuyển request đó sang `http://localhost:5134/api/posts` (Backend). Nhờ vậy Frontend không cần biết Backend chạy ở đâu.

> **Quan trọng**: Phải chạy Backend **trước**, Frontend **sau**. Nếu không, proxy sẽ lỗi.

### 5.5 Cấu trúc Frontend

```
src/frontend/src/
├── main.jsx              ← Entry point, render <App />
├── App.jsx               ← Router: định nghĩa 5 routes
├── index.css             ← Import TailwindCSS
├── services/
│   └── api.js            ← Axios client — TẤT CẢ API call ở đây
├── components/
│   ├── Navbar.jsx        ← Thanh điều hướng (chung cho mọi trang)
│   └── PostCard.jsx      ← Card hiển thị 1 bài viết
└── pages/
    ├── HomePage.jsx       ← Trang chủ — danh sách bài viết
    ├── LoginPage.jsx      ← Đăng nhập / Đăng ký
    ├── PostDetailPage.jsx ← Chi tiết bài viết (⭐ demo Cache-Aside)
    └── CreateEditPostPage.jsx ← Viết bài mới / Sửa bài
```

### 5.6 Routing (các trang)

| URL | Page | Chức năng |
|---|---|---|
| `/` | `HomePage` | Danh sách bài viết |
| `/login` | `LoginPage` | Đăng nhập / Đăng ký |
| `/posts/:id` | `PostDetailPage` | Xem chi tiết bài viết + đo response time |
| `/posts/new` | `CreateEditPostPage` | Tạo bài viết mới |
| `/posts/:id/edit` | `CreateEditPostPage` | Sửa bài viết |

---

## 6. Giải thích cấu trúc project

### 6.1 Backend — Các tầng và vai trò

```
Controllers/    ← Nhận HTTP request, gọi Services, trả response
    ↓ sử dụng
DTOs/           ← Định nghĩa request body / response body (không liên quan DB)
    ↓ khác với
Models/         ← Định nghĩa cấu trúc document trong MongoDB (BsonId, etc.)
    ↓ được truy cập qua
Data/           ← MongoContext — kết nối MongoDB, expose collections
    ↓ và
Services/       ← Logic thao tác Redis (Cache + Session)
    ↓ được gọi bởi
Middleware/     ← Chạy TRƯỚC mọi request, xác thực session
    ↓ cấu hình trong
Program.cs      ← Đăng ký DI, Middleware pipeline, CORS
```

### 6.2 Dependency Injection (DI) — Tại sao dùng?

Trong `Program.cs`:
```csharp
builder.Services.AddScoped<ICacheService, RedisCacheService>();
builder.Services.AddScoped<ISessionService, RedisSessionService>();
```

**Nghĩa là**: Khi Controller cần `ICacheService`, .NET tự động tạo `RedisCacheService` và inject vào constructor. Controller không cần biết implementation cụ thể.

```csharp
// Controller chỉ biết interface
public PostsController(MongoContext mongo, ICacheService cacheService)
{
    _mongo = mongo;          // .NET tự inject MongoContext (Singleton)
    _cacheService = cacheService;  // .NET tự inject RedisCacheService (Scoped)
}
```

### 6.3 Models vs DTOs — Khác nhau thế nào?

- **Model** (`Post.cs`, `User.cs`): Mapping 1-1 với document MongoDB. Có `[BsonId]` attribute. Chứa field nhạy cảm (PasswordHash).
- **DTO** (`CreatePostRequest`, `PostResponse`): Dữ liệu gửi/nhận qua API. **Không** chứa field nhạy cảm. Có `[Required]` validation.

Ví dụ: `LoginRequest` chỉ có `Username + Password`, nhưng `User` model có thêm `Id`, `PasswordHash`, `CreatedAt`.

---

## 7. Luồng hoạt động chính

### 7.1 Luồng Đăng nhập (Session)

```
Người dùng → nhập username + password trên LoginPage
    ↓
Frontend gọi POST /api/auth/login { username, password }
    ↓
AuthController.Login():
    1. Tìm user trong MongoDB theo username
    2. So sánh password hash (BCrypt.Verify)
    3. Nếu đúng → tạo sessionId = Guid.NewGuid()
    4. Gọi _sessionService.CreateSessionAsync(sessionId, ...)
       → Redis: HSET "session:{guid}" userId "xxx" username "admin" loginAt "1724..."
       → Redis: EXPIRE "session:{guid}" 1800  (TTL 30 phút)
    5. Set Cookie: SessionId = {guid}
    6. Trả về { sessionId, username }
    ↓
Frontend nhận response → lưu state → chuyển về trang chủ
```

### 7.2 Luồng Xác thực Session (Middleware)

```
Mỗi request đi vào Backend:
    ↓
SessionAuthMiddleware.InvokeAsync():
    1. Đọc Cookie "SessionId" từ request
    2. Nếu có → gọi sessionService.GetSessionAsync(sessionId)
       → Redis: HGETALL "session:{guid}"
    3. Nếu session tồn tại:
       - HttpContext.Items["UserId"] = session["userId"]
       - HttpContext.Items["Username"] = session["username"]
       (Tùy chọn) Refresh TTL
    4. Nếu không có session → bỏ qua, để Controller xử lý
    5. Gọi await _next(context) → chuyển tiếp tới Controller
```

### 7.3 Luồng Cache-Aside (⭐ Cốt lõi đề tài)

```
Người dùng → click vào bài viết → Frontend gọi GET /api/posts/{id}
    ↓
PostsController.GetById(id):

    ┌─ Bước 1: Kiểm tra Cache ─────────────────────────┐
    │  var cached = await _cacheService.GetAsync("post:{id}");        │
    │  → Redis: GET "post:{id}"                         │
    │                                                    │
    │  Nếu cached != null  →  CACHE HIT ⚡ (<5ms)       │
    │    Deserialize JSON → trả về ngay                  │
    │    (KHÔNG cần truy cập MongoDB)                    │
    └────────────────────────────────────────────────────┘
            │ null (CACHE MISS)
            ▼
    ┌─ Bước 2: Đọc từ MongoDB ─────────────────────────┐
    │  var post = await _mongo.Posts                     │
    │      .Find(p => p.Id == id)                        │
    │      .FirstOrDefaultAsync();                       │
    │  → MongoDB query (~200ms)                          │
    └────────────────────────────────────────────────────┘
            │
            ▼
    ┌─ Bước 3: Ghi ngược vào Cache ────────────────────┐
    │  var json = JsonSerializer.Serialize(post);        │
    │  await _cacheService.SetAsync("post:{id}", json,   │
    │      TimeSpan.FromMinutes(10));                     │
    │  → Redis: SET "post:{id}" "{json}" EX 600          │
    └────────────────────────────────────────────────────┘
            │
            ▼
    Trả về PostResponse cho Frontend
    → Lần tiếp theo gọi cùng endpoint → Bước 1 sẽ HIT!
```

### 7.4 Luồng Cache Invalidation

```
Người dùng → sửa bài viết → Frontend gọi PUT /api/posts/{id}
    ↓
PostsController.Update(id, request):
    1. Cập nhật bài viết trong MongoDB
    2. ⭐ XÓA cache cũ:
       await _cacheService.RemoveAsync("post:{id}");
       → Redis: DEL "post:{id}"
    3. Trả về PostResponse
    ↓
Lần tiếp theo có ai đọc bài viết này:
    → Cache Miss → đọc MongoDB (dữ liệu mới) → ghi lại Cache
    → Đảm bảo dữ liệu luôn nhất quán!
```

### 7.5 Luồng INCR lượt xem

```
Mỗi khi user mở bài viết → Frontend gọi POST /api/posts/{id}/view
    ↓
PostsController.IncrementView(id):
    await _cacheService.IncrementAsync("post_views:{id}");
    → Redis: INCR "post_views:{id}"
    → Redis tự tăng giá trị lên 1 (atomic, real-time)
    → Trả về số lượt xem mới

Đặc điểm: INCR trên Redis cực nhanh, không cần đọc-sửa-ghi,
phù hợp đếm real-time ngay cả khi 1000 người cùng xem.
```

---

## 8. Thiết kế dữ liệu trên Redis

> Phần này quan trọng cho tiêu chí **"Thiết kế mô hình dữ liệu" (1.5đ)**.

### 8.1 Bảng Key Design

| Key Pattern | Redis Data Type | Mục đích | TTL | Lệnh chính |
|---|---|---|---|---|
| `post:{objectId}` | **String** (JSON) | Cache bài viết (Cache-Aside) | 10 phút | `GET`, `SET ... EX 600`, `DEL` |
| `post_views:{objectId}` | **String** (số nguyên) | Bộ đếm lượt xem real-time | Không TTL | `INCR`, `GET` |
| `session:{guid}` | **Hash** | Phiên đăng nhập người dùng | 30 phút | `HSET`, `HGETALL`, `EXPIRE`, `DEL` |

### 8.2 Ví dụ cụ thể trong Redis

```
# Cache bài viết (String chứa JSON)
KEY:   post:64a1b2c3d4e5f6
TYPE:  string
VALUE: {"Id":"64a1b2c3d4e5f6","Title":"Tin hot","Content":"...","Views":42,...}
TTL:   600 (10 phút, đếm ngược)

# Bộ đếm lượt xem (String chứa số)
KEY:   post_views:64a1b2c3d4e5f6
TYPE:  string
VALUE: "150"
TTL:   -1 (không hết hạn)

# Session người dùng (Hash)
KEY:   session:a1b2c3d4-e5f6-7890-abcd-ef1234567890
TYPE:  hash
FIELDS:
  userId   → "64a1b2c3d4e5f6"
  username → "nguyenvana"
  loginAt  → "1724150400"
TTL:   1800 (30 phút, đếm ngược)
```

### 8.3 Tại sao dùng Hash cho Session? (câu hỏi demo)

- Hash cho phép **truy cập từng field** mà không cần deserialize toàn bộ JSON
- Ví dụ: `HGET session:xxx username` → lấy riêng username, nhanh hơn `GET` rồi parse JSON
- Mỗi field hoạt động độc lập, có thể `HSET` thêm field mà không ảnh hưởng field khác
- Phù hợp cho session vì có nhiều thuộc tính nhỏ (userId, username, loginAt, ...)

### 8.4 Tại sao dùng String cho Cache bài viết?

- Bài viết có `Content` rất dài (nhiều đoạn văn) → phù hợp lưu dạng JSON string
- Chỉ cần `GET/SET/DEL`, không cần truy cập từng field riêng lẻ
- Đơn giản, hiệu quả cho pattern Cache-Aside

---

## 9. Hướng dẫn SV1 — Data Architect & CRUD Lead

### 9.1 Nhiệm vụ tổng quan

Bạn phụ trách **thiết kế DB gốc** và **API CRUD cơ bản** — phần nền tảng mà SV2 và SV3 sẽ build tiếp lên.

### 9.2 Cách tìm TODO của bạn

```bash
cd src/NewsCacheSession.Api
grep -rn "TODO \[SV1\]" .
```

### 9.3 File 1: `Controllers/AuthController.cs`

#### Endpoint 1: `POST /api/auth/register`

```csharp
[HttpPost("register")]
public async Task<IActionResult> Register([FromBody] RegisterRequest request)
{
    // Bước 1: Kiểm tra username đã tồn tại
    var existingUser = await _mongo.Users
        .Find(u => u.Username == request.Username)
        .FirstOrDefaultAsync();

    if (existingUser != null)
        return Conflict(new { message = "Username đã tồn tại" });

    // Bước 2: Hash password
    // Cách 1 — BCrypt (cần: dotnet add package BCrypt.Net-Next)
    var hash = BCrypt.Net.BCrypt.HashPassword(request.Password);

    // Cách 2 — SHA256 (không cần thêm package, nhưng kém an toàn hơn)
    // using System.Security.Cryptography;
    // var hash = Convert.ToHexString(SHA256.HashData(
    //     System.Text.Encoding.UTF8.GetBytes(request.Password)));

    // Bước 3: Tạo User mới
    var user = new User
    {
        Username = request.Username,
        PasswordHash = hash,
        CreatedAt = DateTime.UtcNow
    };

    // Bước 4: Lưu vào MongoDB
    await _mongo.Users.InsertOneAsync(user);

    // Bước 5: Trả về 201 Created
    return Created("", new { message = "Đăng ký thành công", userId = user.Id });
}
```

#### Endpoint 2: `POST /api/auth/login`

```csharp
[HttpPost("login")]
public async Task<IActionResult> Login([FromBody] LoginRequest request)
{
    // Bước 1: Tìm user
    var user = await _mongo.Users
        .Find(u => u.Username == request.Username)
        .FirstOrDefaultAsync();

    if (user == null)
        return Unauthorized(new { message = "Sai username hoặc password" });

    // Bước 2: Verify password
    if (!BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
        return Unauthorized(new { message = "Sai username hoặc password" });

    // Bước 3: Tạo session
    var sessionId = Guid.NewGuid().ToString();
    var ttl = TimeSpan.FromMinutes(30);

    // Bước 4: Lưu session vào Redis (Hashes + TTL)
    await _sessionService.CreateSessionAsync(sessionId, user.Id, user.Username, ttl);

    // Bước 5: Set Cookie
    Response.Cookies.Append("SessionId", sessionId, new CookieOptions
    {
        HttpOnly = true,
        MaxAge = ttl,
        SameSite = SameSiteMode.Lax
    });

    // Bước 6: Trả về response
    return Ok(new LoginResponse
    {
        SessionId = sessionId,
        Username = user.Username
    });
}
```

#### Endpoint 3: `POST /api/auth/logout`

```csharp
[HttpPost("logout")]
public async Task<IActionResult> Logout()
{
    var sessionId = Request.Cookies["SessionId"];
    if (!string.IsNullOrEmpty(sessionId))
    {
        await _sessionService.RemoveSessionAsync(sessionId);
        Response.Cookies.Delete("SessionId");
    }
    return Ok(new { message = "Đăng xuất thành công" });
}
```

#### Endpoint 4: `GET /api/auth/me`

```csharp
[HttpGet("me")]
public async Task<IActionResult> Me()
{
    var sessionId = Request.Cookies["SessionId"];
    if (string.IsNullOrEmpty(sessionId))
        return Unauthorized();

    var session = await _sessionService.GetSessionAsync(sessionId);
    if (session == null)
        return Unauthorized();

    return Ok(new SessionInfoResponse
    {
        UserId = session["userId"],
        Username = session["username"],
        LoginAt = session["loginAt"]
    });
}
```

### 9.4 File 2: `Controllers/PostsController.cs` (phần CRUD)

#### Endpoint: `GET /api/posts` (Danh sách + phân trang)

```csharp
[HttpGet]
public async Task<IActionResult> GetAll([FromQuery] int page = 1, [FromQuery] int pageSize = 10)
{
    var posts = await _mongo.Posts
        .Find(_ => true)                           // Lấy tất cả
        .SortByDescending(p => p.CreatedAt)         // Mới nhất trước
        .Skip((page - 1) * pageSize)                // Phân trang
        .Limit(pageSize)
        .ToListAsync();

    var response = posts.Select(p => new PostResponse
    {
        Id = p.Id,
        Title = p.Title,
        Content = p.Content,
        ImageUrl = p.ImageUrl,
        AuthorId = p.AuthorId,
        Views = p.Views,
        CreatedAt = p.CreatedAt,
        UpdatedAt = p.UpdatedAt
    });

    return Ok(response);
}
```

#### Endpoint: `POST /api/posts` (Tạo bài mới)

```csharp
[HttpPost]
public async Task<IActionResult> Create([FromBody] CreatePostRequest request)
{
    // Kiểm tra đăng nhập (middleware đã set HttpContext.Items)
    var userId = HttpContext.Items["UserId"]?.ToString();
    if (string.IsNullOrEmpty(userId))
        return Unauthorized(new { message = "Vui lòng đăng nhập" });

    var post = new Post
    {
        Title = request.Title,
        Content = request.Content,
        ImageUrl = request.ImageUrl,
        AuthorId = userId,
        Views = 0,
        CreatedAt = DateTime.UtcNow,
        UpdatedAt = DateTime.UtcNow
    };

    await _mongo.Posts.InsertOneAsync(post);

    return Created($"/api/posts/{post.Id}", new PostResponse
    {
        Id = post.Id,
        Title = post.Title,
        Content = post.Content,
        ImageUrl = post.ImageUrl,
        AuthorId = post.AuthorId,
        Views = post.Views,
        CreatedAt = post.CreatedAt,
        UpdatedAt = post.UpdatedAt
    });
}
```

#### Endpoint: `DELETE /api/posts/{id}` (Soft Delete + Cache Invalidation)

```csharp
[HttpDelete("{id}")]
public async Task<IActionResult> Delete(string id)
{
    if (!ObjectId.TryParse(id, out var objectId))
        return BadRequest(new { message = "ID bài viết không hợp lệ." });

    var filter = Builders<Post>.Filter.And(
        new BsonDocument("_id", objectId),
        new BsonDocument("$or", new BsonArray
        {
            new BsonDocument("IsDeleted", false),
            new BsonDocument("IsDeleted", new BsonDocument("$exists", false))
        }));

    var now = DateTime.UtcNow;
    var update = Builders<Post>.Update
        .Set(p => p.IsDeleted, true)
        .Set(p => p.DeletedAt, now)
        .Set(p => p.UpdatedAt, now);

    var result = await _mongo.Posts.UpdateOneAsync(filter, update);

    if (result.MatchedCount == 0)
        return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });

    // Cache Invalidation — xóa nội dung và bộ đếm cũ trong Redis
    await Task.WhenAll(
        _cacheService.RemoveAsync(CachePrefix + id),
        _cacheService.RemoveAsync(ViewsPrefix + id));

    return NoContent();
}
```

### 9.5 Import cần thêm

Nếu dùng BCrypt, thêm vào đầu `AuthController.cs`:
```csharp
// Không cần using — BCrypt.Net tự expose qua namespace
```

Và cài package:
```bash
cd src/NewsCacheSession.Api
dotnet add package BCrypt.Net-Next
```

---

## 10. Hướng dẫn SV2 — Advanced Query Specialist

### 10.1 Nhiệm vụ tổng quan

Bạn phụ trách phần **nâng cao đặc trưng (2.5đ)**: Cache-Aside Pattern, Cache Invalidation, Session Middleware, và bộ đếm INCR.

### 10.2 Cách tìm TODO của bạn

```bash
cd src/NewsCacheSession.Api
grep -rn "TODO \[SV2\]" .
```

### 10.3 File 1: `Middleware/SessionAuthMiddleware.cs`

```csharp
public async Task InvokeAsync(HttpContext context, ISessionService sessionService)
{
    // Bước 1: Đọc SessionId
    var sessionId = context.Request.Cookies["SessionId"]
                 ?? context.Request.Headers["X-Session-Id"].FirstOrDefault();

    // Bước 2: Nếu có session → kiểm tra Redis
    if (!string.IsNullOrEmpty(sessionId))
    {
        var session = await sessionService.GetSessionAsync(sessionId);

        if (session != null)
        {
            // Bước 3: Gán thông tin user vào HttpContext
            context.Items["UserId"] = session["userId"];
            context.Items["Username"] = session["username"];

            // (Tuỳ chọn) Refresh TTL mỗi request
            // await sessionService.RefreshSessionAsync(sessionId, TimeSpan.FromMinutes(30));
        }
    }

    // Bước 4: Chuyển tiếp — LUÔN LUÔN gọi _next
    await _next(context);
}
```

> **Lưu ý quan trọng**: `await _next(context)` phải LUÔN được gọi, dù session có hay không. Nếu thiếu dòng này, mọi request sẽ bị treo.

### 10.4 File 2: `Controllers/PostsController.cs` (phần nâng cao)

#### Endpoint: `GET /api/posts/{id}` — ⭐ Cache-Aside Pattern

```csharp
using System.Text.Json;   // Thêm ở đầu file

[HttpGet("{id}")]
public async Task<IActionResult> GetById(string id)
{
    // ====== BƯỚC 1: KIỂM TRA CACHE ======
    var cached = await _cacheService.GetAsync(CachePrefix + id);

    if (cached != null)
    {
        // CACHE HIT — trả về ngay, không cần truy cập MongoDB
        var cachedPost = JsonSerializer.Deserialize<PostResponse>(cached);
        return Ok(cachedPost);
    }

    // ====== BƯỚC 2: CACHE MISS — ĐỌC TỪ MONGODB ======
    var post = await _mongo.Posts
        .Find(p => p.Id == id)
        .FirstOrDefaultAsync();

    if (post == null)
        return NotFound(new { message = "Bài viết không tồn tại" });

    var response = new PostResponse
    {
        Id = post.Id,
        Title = post.Title,
        Content = post.Content,
        ImageUrl = post.ImageUrl,
        AuthorId = post.AuthorId,
        Views = post.Views,
        CreatedAt = post.CreatedAt,
        UpdatedAt = post.UpdatedAt
    };

    // ====== BƯỚC 3: GHI NGƯỢC VÀO REDIS + TTL ======
    var json = JsonSerializer.Serialize(response);
    await _cacheService.SetAsync(CachePrefix + id, json, CacheTtl);
    // Redis command: SET "post:{id}" "{json}" EX 600

    // ====== BƯỚC 4: TRẢ VỀ ======
    return Ok(response);
}
```

#### Endpoint: `PUT /api/posts/{id}` — Cache Invalidation

```csharp
[HttpPut("{id}")]
public async Task<IActionResult> Update(string id, [FromBody] UpdatePostRequest request)
{
    // Bước 1: Tìm và cập nhật trong MongoDB
    var filter = Builders<Post>.Filter.Eq(p => p.Id, id);
    var update = Builders<Post>.Update
        .Set(p => p.Title, request.Title)
        .Set(p => p.Content, request.Content)
        .Set(p => p.ImageUrl, request.ImageUrl)
        .Set(p => p.UpdatedAt, DateTime.UtcNow);

    var result = await _mongo.Posts.UpdateOneAsync(filter, update);

    if (result.MatchedCount == 0)
        return NotFound();

    // ⭐ Bước 2: CACHE INVALIDATION — xóa cache cũ
    await _cacheService.RemoveAsync(CachePrefix + id);
    // Redis command: DEL "post:{id}"
    // → Lần đọc tiếp theo sẽ Cache Miss → lấy dữ liệu mới từ MongoDB

    // Bước 3: Trả về bài viết đã cập nhật
    var updated = await _mongo.Posts.Find(p => p.Id == id).FirstOrDefaultAsync();
    return Ok(new PostResponse
    {
        Id = updated.Id,
        Title = updated.Title,
        Content = updated.Content,
        ImageUrl = updated.ImageUrl,
        AuthorId = updated.AuthorId,
        Views = updated.Views,
        CreatedAt = updated.CreatedAt,
        UpdatedAt = updated.UpdatedAt
    });
}
```

> **Import cần thêm** ở đầu `PostsController.cs`:
> ```csharp
> using System.Text.Json;
> using MongoDB.Driver;     // Cho Builders<Post>
> using NewsCacheSession.Api.Models;  // Cho Post class
> ```

#### Endpoint: `POST /api/posts/{id}/view` — INCR bộ đếm

```csharp
[HttpPost("{id}/view")]
public async Task<IActionResult> IncrementView(string id)
{
    // INCR — tăng lượt xem lên 1 (atomic operation)
    var newCount = await _cacheService.IncrementAsync(ViewsPrefix + id);
    // Redis command: INCR "post_views:{id}"

    return Ok(new { views = newCount });
}
```

### 10.5 Checklist kiểm tra sau khi implement

- [ ] Gọi `GET /api/posts/{id}` lần 1 → kiểm tra Redis có key `post:{id}` (dùng `redis-cli GET "post:{id}"`)
- [ ] Gọi `GET /api/posts/{id}` lần 2 → response nhanh hơn hẳn
- [ ] Gọi `PUT /api/posts/{id}` → kiểm tra `redis-cli GET "post:{id}"` → nil (đã bị xóa)
- [ ] Gọi `POST /api/posts/{id}/view` nhiều lần → `redis-cli GET "post_views:{id}"` tăng dần
- [ ] Đăng nhập → `redis-cli HGETALL "session:{guid}"` → thấy userId, username, loginAt
- [ ] Đợi 30 phút (hoặc `redis-cli EXPIRE "session:{guid}" 5`) → session tự hết hạn

---

## 11. Hướng dẫn SV3 — Fullstack Integrator & DB Tester

### 11.1 Nhiệm vụ tổng quan

Bạn phụ trách **Frontend UI**, **nạp 100 bài viết mẫu**, và **đo hiệu năng** (benchmark DB vs Cache).

### 11.2 Cách tìm TODO của bạn

```bash
# Frontend
grep -rn "TODO \[SV3\]" src/frontend/src/

# Scripts
grep -rn "TODO \[SV3\]" scripts/
```

### 11.3 Frontend — Implement các pages

Mỗi page đã có skeleton + TODO. Chỉ cần **uncomment code mẫu** trong TODO và điều chỉnh.

Tất cả API call đã được khai báo sẵn trong `src/frontend/src/services/api.js`:

```javascript
// Sử dụng:
import { authApi, postsApi } from '../services/api';

// Đăng nhập
const res = await authApi.login(username, password);

// Lấy danh sách bài viết
const res = await postsApi.getAll(page, pageSize);

// Lấy chi tiết (Cache-Aside)
const res = await postsApi.getById(id);

// Tăng lượt xem (INCR)
await postsApi.incrementView(id);
```

#### Tip: Đo response time cho demo (PostDetailPage)

```javascript
useEffect(() => {
    const fetchPost = async () => {
        const start = performance.now();
        try {
            const res = await postsApi.getById(id);
            const elapsed = (performance.now() - start).toFixed(2);
            setPost(res.data);
            setResponseTime(elapsed);
            // elapsed > 100ms → Cache Miss 🐌
            // elapsed < 20ms  → Cache Hit ⚡
        } catch {
            navigate('/');
        } finally {
            setLoading(false);
        }
    };

    fetchPost();
    postsApi.incrementView(id); // Tăng lượt xem
}, [id]);
```

#### Tip: TailwindCSS cheat sheet

```html
<!-- Layout -->
className="flex items-center justify-between"
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
className="max-w-6xl mx-auto px-4 py-8"

<!-- Typography -->
className="text-3xl font-bold text-gray-800"
className="text-sm text-gray-500"

<!-- Button -->
className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"

<!-- Card -->
className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"

<!-- Input -->
className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
```

### 11.4 Script 1: Seed 100 bài viết (`scripts/SeedPosts/seed.py`)

```python
"""
Nạp 100 bài viết mẫu vào MongoDB.
Cài đặt: pip install pymongo faker
Chạy:    python scripts/SeedPosts/seed.py
"""

from pymongo import MongoClient
from faker import Faker
from datetime import datetime
import random

fake = Faker('vi_VN')  # Faker tiếng Việt

# Kết nối MongoDB (cùng config với appsettings.json)
client = MongoClient("mongodb://localhost:27017")
db = client["newsdb"]
collection = db["posts"]

# Xóa bài cũ (nếu muốn reset)
# collection.delete_many({})

posts = []
for i in range(100):
    created = fake.date_time_this_year()
    posts.append({
        "Title": fake.sentence(nb_words=8),
        "Content": "\n\n".join(fake.paragraphs(nb=random.randint(3, 6))),
        "ImageUrl": f"https://picsum.photos/seed/{i + 1}/800/400",
        "AuthorId": None,
        "Views": random.randint(0, 500),
        "CreatedAt": created,
        "UpdatedAt": created,
    })

result = collection.insert_many(posts)
print(f"✅ Đã nạp {len(result.inserted_ids)} bài viết vào MongoDB (newsdb.posts)")
print(f"   Ví dụ ID: {result.inserted_ids[0]}")
```

**Chạy**:
```bash
pip install pymongo faker
python scripts/SeedPosts/seed.py
```

**Kiểm tra**: Mở MongoDB Compass → `newsdb` → `posts` → phải thấy 100 documents.

### 11.5 Script 2: Benchmark DB vs Cache (`scripts/Benchmark/benchmark.py`)

```python
"""
So sánh thời gian đọc bài viết: DB gốc (Cache Miss) vs Redis (Cache Hit).
Cài đặt: pip install requests matplotlib
Chạy:    python scripts/Benchmark/benchmark.py
(Yêu cầu: Backend đang chạy ở http://localhost:5134)
"""

import requests
import time
import matplotlib.pyplot as plt

BASE_URL = "http://localhost:5134/api"

# Bước 1: Lấy 1 post ID từ danh sách
print("🔍 Lấy danh sách bài viết...")
res = requests.get(f"{BASE_URL}/posts?page=1&pageSize=1")
posts = res.json()

if not posts:
    print("❌ Chưa có bài viết! Chạy seed.py trước.")
    exit()

post_id = posts[0]["id"]
print(f"   Dùng bài viết: {post_id}")

# Bước 2: Xóa cache để đảm bảo Cache Miss
import subprocess
subprocess.run(["redis-cli", "DEL", f"post:{post_id}"], capture_output=True)
print("🗑️ Đã xóa cache")

# Bước 3: Lần 1 — Cache Miss (đọc MongoDB)
print("\n⏱️ Lần 1 — Cache Miss (MongoDB)...")
start = time.time()
res = requests.get(f"{BASE_URL}/posts/{post_id}")
time_db = (time.time() - start) * 1000
print(f"   Thời gian: {time_db:.2f}ms")

# Bước 4: Lần 2 — Cache Hit (đọc Redis)
print("\n⏱️ Lần 2 — Cache Hit (Redis)...")
start = time.time()
res = requests.get(f"{BASE_URL}/posts/{post_id}")
time_cache = (time.time() - start) * 1000
print(f"   Thời gian: {time_cache:.2f}ms")

# Bước 5: Tính tốc độ tăng
speedup = time_db / time_cache if time_cache > 0 else 0
print(f"\n🚀 Tốc độ nhanh hơn: {speedup:.1f}x")

# Bước 6: Vẽ biểu đồ
labels = ['Cache Miss\n(MongoDB)', 'Cache Hit\n(Redis)']
times = [time_db, time_cache]
colors = ['#ef4444', '#22c55e']

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(labels, times, color=colors, width=0.5)

# Hiện giá trị trên cột
for bar, t in zip(bars, times):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
            f'{t:.2f}ms', ha='center', va='bottom', fontweight='bold')

ax.set_ylabel('Thời gian (ms)')
ax.set_title('So Sánh Thời Gian: MongoDB vs Redis Cache')
ax.set_ylim(0, max(times) * 1.3)

plt.tight_layout()
plt.savefig('scripts/Benchmark/benchmark_result.png', dpi=150)
print(f"\n📊 Biểu đồ đã lưu: scripts/Benchmark/benchmark_result.png")
plt.show()
```

**Chạy**:
```bash
pip install requests matplotlib
python scripts/Benchmark/benchmark.py
```

---

## 12. Kịch bản Demo Bảo Vệ

### Chuẩn bị trước demo

1. Chạy MongoDB + Redis
2. Chạy Backend: `cd src/NewsCacheSession.Api && dotnet run`
3. Chạy Frontend: `cd src/frontend && npm run dev`
4. Đã chạy `seed.py` (100 bài viết)
5. Mở **Redis Insight** → kết nối `localhost:6379`
6. Mở trình duyệt → `http://localhost:3000`

### Kịch bản từng bước

| Bước | Ai | Hành động | Kết quả | Chứng minh điều gì |
|---|---|---|---|---|
| 1 | SV3 | Mở trang chi tiết bài viết + F12 Network | Response `~50-200ms` | **Cache Miss** — dữ liệu từ MongoDB |
| 2 | SV3 | **Refresh lại** cùng trang (F5) | Response `<10ms` | **Cache Hit** — dữ liệu từ Redis, nhanh gấp 10-40x |
| 3 | SV3 | Mở Redis Insight → tìm key `post:{id}` | Thấy JSON bài viết + TTL đếm ngược | Cache-Aside đã ghi ngược Redis + TTL |
| 4 | SV1 | Sửa nội dung bài viết (qua Swagger hoặc UI) | Bài viết cập nhật trong MongoDB | CRUD cơ bản hoạt động |
| 5 | SV2 | Mở Redis Insight → tìm key `post:{id}` | Key **biến mất** (nil) | **Cache Invalidation** — cache bị xóa khi sửa |
| 6 | SV3 | Load lại bài viết | Response `~50-200ms` + nội dung MỚI | Cache Miss lại → lấy dữ liệu mới từ MongoDB |
| 7 | SV3 | Mở Redis Insight → tìm key `session:*` | Thấy Hash: userId, username, loginAt | **Hashes** lưu Session |
| 8 | SV3 | Quan sát TTL của session key | TTL đếm ngược (1800 → 1799 → ...) | **TTL/EXPIRE** hoạt động |
| 9 | SV2 | Click vào bài viết nhiều lần | `post_views:{id}` tăng dần | **INCR** bộ đếm real-time |

---

## 13. Lỗi thường gặp & Cách sửa

### Backend

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `MongoConnectionException` | MongoDB chưa chạy | Chạy `mongod` hoặc start service MongoDB |
| `RedisConnectionException` | Redis chưa chạy | Chạy `redis-server` hoặc start service Redis |
| `500 NotImplementedException` | Endpoint chưa implement | Bình thường! Replace `throw` bằng code thật |
| `404 Not Found` trên Swagger | Sai URL hoặc chưa MapControllers | Kiểm tra route `[Route("api/[controller]")]` |
| `415 Unsupported Media Type` | Request thiếu `Content-Type` | Thêm header `Content-Type: application/json` |

### Frontend

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `ERR_CONNECTION_REFUSED` khi gọi API | Backend chưa chạy | Chạy Backend trước, Frontend sau |
| `Network Error` | Proxy sai port | Kiểm tra `vite.config.js` proxy target = `http://localhost:5134` |
| Trang trắng | Error trong component | Mở F12 Console → xem lỗi JS |
| TailwindCSS không hoạt động | Thiếu import | Kiểm tra `index.css` có `@import "tailwindcss";` |

### Redis

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `(error) WRONGTYPE` | Dùng GET trên Hash key (hoặc ngược lại) | Dùng `HGETALL` cho Hash, `GET` cho String |
| Key không tồn tại sau 10 phút | TTL hết hạn | Bình thường! Đó chính là Cache-Aside |
| `FLUSHALL` mất hết data | Đã xóa toàn bộ Redis | Đăng nhập lại + load lại bài viết để tạo cache mới |
