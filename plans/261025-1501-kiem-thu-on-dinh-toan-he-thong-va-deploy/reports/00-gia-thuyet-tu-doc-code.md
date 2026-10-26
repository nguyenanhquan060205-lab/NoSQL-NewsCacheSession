# Giả thuyết lỗi rút ra từ đọc code và chạy baseline — 25/10/2026

Đây là **danh sách việc cần chứng minh hoặc bác bỏ**, chưa phải kết luận. Mỗi dòng có file:line
để `/ak-debug` bắt đầu từ đó. Mã `G..` chỉ dùng trong plan này, không ghi vào code hay commit.

Mức: **Cao** = có thể hỏng demo/barem hoặc hỏng deploy · **TB** = sai hành vi khi có sự cố ·
**Thấp** = cần biết để trả lời phản biện.

## A. Môi trường và baseline (đã kiểm chứng tối 25/10)

| # | Mức | Hiện tượng đã thấy | Bằng chứng |
|---|---|---|---|
| G1 | Cao | Máy có **hai MongoDB**: `mongod` cài native chiếm `127.0.0.1:27017` (chỉ có `qlsinhvien_db` của project khác), container `news-mongo` bị map ra **27018** (chứa `newsdb`, 10 150 bài chưa xóa). `docker-compose.yml:7` khai `27017:27017`. Chạy API theo README (không biến môi trường) sẽ đọc kho **rỗng**. | `lsof -iTCP:27017`, `docker ps`, mongosh |
| G2 | Cao | API đang chạy (PID 59923) khởi động **23/10 14:37**, cũ hơn PR #23 và có thể cũ hơn bản sửa lượt xem chưa commit. API này chạy được là nhờ biến `MongoSettings__ConnectionString` trỏ sang container. Kiểm thử trên tiến trình này là kiểm thử **mã cũ**. | `ps -o lstart -p 59923`, `ps eww` |
| G3 | Cao | Redis demo (DB 0) hiện chỉ có **1 key** — chưa đạt định mức 20–50 key có TTL khác nhau. | `redis-cli INFO keyspace` |
| G4 | Cao | `seed_redis.py` chỉ chấp nhận đúng `mongodb://localhost:27017` + `redis://localhost:6379/0` + DB `newsdb`; máy này Mongo ở 27018 nên script **từ chối chạy** → không seed được G3. | `scripts/SeedRedis/seed_redis.py:267-269` |
| G5 | TB | 2 unit test của SeedRedis đang fail: `test_verifier_default_no_api_calls` (`1 != 0`) và `test_verifier_missing_key_nonzero` (`KeyError: 'missingOrInvalid'`). Doc 23/10 ghi 33/33 pass → có thể đã hồi quy, hoặc test phụ thuộc trạng thái Redis thật. | `python3 -m unittest discover` trong `scripts/SeedRedis` |
| G6 | Thấp | Python hệ thống thiếu `pytest`, `pymongo`, `bson` → test SeedPosts không import được. Cần venv riêng. | `python3 -m unittest discover` trong `scripts/SeedPosts` |
| G7 | Thấp | Baseline xanh: .NET 27/27, Vitest 103/103, `oxlint` sạch. **Nhưng xanh không chứng minh nhiều** — xem G8. | `dotnet test`, `npx vitest run` |
| G27 | Cao | **`main` trên GitHub không build được project test**: 6 chỗ gọi `new PostsController(null!, cache, currentUser)` (3 tham số) trong khi constructor đã thành 5 tham số từ SCRUM-39. Baseline xanh chỉ vì working tree có bản vá chưa commit. **Đã vá** ở commit `9665335` trên nhánh `develop`. | `git show HEAD:tests/.../PostsControllerCacheAsideTests.cs`, commit `c60caf6` |
| G28 | Cao (barem 1.5đ) | Key `posts:dirty_views` (Set, không TTL) do worker lượt xem dùng **không có trong `docs/redis-keyspace.md`** — thầy đối chiếu doc với RedisInsight sẽ thấy key lạ. Doc còn ghi `SET lock:post:{id} 1 NX PX 5000` trong khi code ghi token GUID. | `Services/RedisCacheService.cs:76,81`, `docs/redis-keyspace.md:13,71` |

## B. Chất lượng bằng chứng test

| # | Mức | Vấn đề | Bằng chứng |
|---|---|---|---|
| G8 | Cao | `Integration/CacheInvalidationTests.cs` gọi thẳng **chính cái mock** rồi verify mock — không đi qua controller, không chứng minh invalidation. Toàn bộ test .NET dùng mock; CRUD/đăng nhập của SV1 **không có test tự động nào**. | `tests/NewsCacheSession.Tests/Integration/CacheInvalidationTests.cs:25-54` |

## C. Backend — phần SV2 (Quân)

| # | Mức | Giả thuyết | Bằng chứng |
|---|---|---|---|
| G9 | TB→Cao khi deploy | **Redis sập thì gần như cả API trả 500**: `GetById`/`GetAll` gọi Redis không bắt lỗi; middleware gọi `HGETALL` cho **mọi** request có cookie → cả endpoint chỉ đọc Mongo cũng 500. Redis Cloud gói free giới hạn 30 kết nối, 100 ops/s nên lỗi Redis trên production dễ xảy ra hơn local. | `Controllers/PostsController.cs:88,166,181`, `Middleware/SessionAuthMiddleware.cs:25,39`, `Services/RedisCacheService.cs:21-55` |
| G10 | TB | `GetById` không lấy được lock thì **đệ quy không giới hạn** (`Task.Delay(50)` rồi gọi lại chính nó). Lock có TTL 5s nên bình thường tối đa ~100 vòng; nhưng nếu sửa G9 theo kiểu "Redis lỗi thì lock trả false" sẽ thành vòng lặp vô hạn. Hai lỗi này phải sửa cùng nhau. | `PostsController.cs:183-188` |
| G11 | Thấp | Worker flush lượt xem đã `SPOP` ID khỏi `posts:dirty_views` rồi mới ghi Mongo; ghi Mongo lỗi thì ID mất khỏi Set, Mongo lệch tới lượt xem kế tiếp. | `Services/ViewCountSyncWorker.cs:53-67` |
| G12 | Thấp | `POST /{id}/view` trên bài đã xóa mềm vẫn đếm nếu key đếm còn (đã ghi nhận #5 trong doc 23/10). | `PostsController.cs:398-411` |
| G13 | Thấp | Bản sửa "khởi tạo bộ đếm từ `posts.views`" (SET NX) **chưa commit** — đang nằm trong working tree trên `main`. | `git status`, `git diff src/` |

## D. Backend — phần SV1 (Như)

| # | Mức | Giả thuyết | Bằng chứng |
|---|---|---|---|
| G14 | TB | `Update`/`Delete` gọi Cloudinary (`HttpClient` mặc định timeout 100s) **trước** khi xóa cache. Cloudinary chậm → request treo, bản cache cũ còn sống trong lúc chờ (chỉ xảy ra khi bài có `imagePublicId`). | `PostsController.cs:322-325, 373-376` |
| G15 | TB | Hai request tạo bài **cùng tiêu đề** chen nhau: `GenerateUniqueSlugAsync` chỉ kiểm tra bằng query, unique index `ux_posts_slug` chặn ở DB nhưng `Create` **không bắt** `DuplicateKey` → 500. | `PostsController.cs:263,272,474-482`, `Data/MongoIndexInitializer.cs:30-34` |
| G16 | Cao khi deploy | **Người đăng ký đầu tiên tự thành admin**, kiểm tra bằng `Any()` rồi mới insert → hai request đăng ký đầu tiên chen nhau đều thành admin. Deploy công khai với collection `users` rỗng thì người lạ đăng ký trước sẽ là admin. | `Controllers/AuthController.cs:59-65` |
| G17 | TB | Cookie `Max-Age=1800` chỉ đặt lúc đăng nhập, không cấp lại khi trượt TTL → dùng liên tục quá 30 phút bị đăng xuất dù Redis còn phiên (#2 doc 23/10). `SessionTtl` hardcode 30 phút, lệch `SessionSettings:TtlMinutes` (#3). | `AuthController.cs:22, 108-114` |
| G18 | Thấp | Đăng nhập ghi session 2 bước không nguyên tử: tạo Hash với `role=user` rồi `TouchAsync` ghi role thật. | `AuthController.cs:99-104`, `Services/RedisSessionService.cs:32-33` |
| G19 | Thấp | DTO không giới hạn độ dài `Title`/`Content`/`Username`; BCrypt chỉ dùng 72 byte đầu của mật khẩu. | `DTOs/Posts/CreatePostRequest.cs`, `DTOs/Auth/RegisterRequest.cs` |

## E. Frontend và script — phần SV3 (Định)

| # | Mức | Giả thuyết | Bằng chứng |
|---|---|---|---|
| G20 | TB | Ở chế độ `npm run dev`, trang chủ gọi API lỗi thì **lặng lẽ hiện bài mẫu giả** (`previewPosts`). Demo chạy bằng `npm run dev` → API chết vẫn thấy tin, dễ tưởng hệ thống ổn. Cần xác nhận banner `isPreview` có đủ nổi không. | `src/frontend/src/pages/HomePage.jsx:65-73,121` |
| G21 | Thấp | Proxy Vite khóa cứng `http://localhost:5134` → muốn chạy UI trỏ vào API QA phải dùng file config riêng (không sửa file của SV3). | `src/frontend/vite.config.js:17-22` |

## F. Deploy

| # | Mức | Giả thuyết | Bằng chứng |
|---|---|---|---|
| G22 | Cao | Chưa có `Dockerfile`/`.dockerignore`; Render cần image hoặc lệnh build. | `ls` gốc repo |
| G23 | Cao | Frontend dùng `BrowserRouter` + `baseURL: '/api'` → trên Vercel cần rewrite `/api/*` sang Render **và** fallback SPA về `index.html`, nếu không thì F5 ở `/posts/{id}` ra 404. Rewrite cùng origin giúp cookie `SameSite=Lax` vẫn chạy. | `src/frontend/src/App.jsx:15`, `src/frontend/src/services/api.js:4-7` |
| G24 | TB | Render free ngủ sau 15 phút, thức dậy mất khoảng 1 phút → lần tải đầu trên production không minh họa được "~200ms vs <5ms"; worker flush lượt xem dừng khi ngủ. Demo chấm điểm phải chạy local. | docs.render.com/free |
| G25 | TB | Redis Cloud free: 30 MB, 30 kết nối, 100 ops/s; Atlas M0: 512 MB, ~100 ops/s → **không chạy benchmark/tải trên production**. Dữ liệu hiện tại 145 MB data / 78.5 MB storage → vừa Atlas M0. | redis.io essentials-plan-details, mongodb.com/pricing, `db.stats()` |
| G26 | TB | Vercel (project tạo sau 06/04/2026) tôn trọng header cache của upstream khi rewrite. API không gửi `Cache-Control` → cần chặn cache `/api/*` rõ ràng để `X-Cache` và dữ liệu không bị CDN giữ. | vercel.com/docs/rewrites |
