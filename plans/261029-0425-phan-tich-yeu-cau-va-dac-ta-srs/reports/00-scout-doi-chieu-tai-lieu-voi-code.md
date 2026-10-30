# Báo cáo scout — đối chiếu tài liệu với code (29/10/2026)

Đầu vào của Phase 1. Đọc trực tiếp code trên nhánh `develop` (commit `dd9d242`), không chạy
stack (Docker daemon đang tắt lúc scout). Mọi dòng có dẫn `file:line`.

## 1. Tình trạng tài liệu

| Tài liệu | Tình trạng |
|---|---|
| `docs/ĐỀ TÀI 06.docx` | Nguồn gốc. 4 mục: barem 10đ, định mức dummy data, phân công 3 SV, kịch bản demo 3 bước |
| `docs/nosql-jira-tasks.csv` | 37 ticket (SCRUM-13 → SCRUM-49). Done 26, Idea 9, In Progress 2 |
| `docs/SRS.md` | **Chưa commit** (`git status`: `??`), sửa lần cuối 29/10 11:20, v2.0. Không có chủ sở hữu trong bảng phân công `AGENTS.md` §4 |
| `docs/redis-keyspace.md`, `docs/mongodb-schema.md` | SV1. Khớp code (commit `4c9a9c9` "đồng bộ keyspace Redis với code thật") |
| `docs/bao-cao-kiem-thu-hieu-nang.md` | SV3. Số đo chính thức 25/10, đã giải thích vì sao không đạt "~200ms vs <5ms" (§5.2) |
| `docs/checklist-barem.md` | SV1. **Lạc hậu**: phần 4 vẫn ghi "chưa có số đo, chưa có biểu đồ" (`docs/checklist-barem.md:22`, `:128`) |
| `AGENTS.md` §6 | **Lạc hậu**: "SessionAuthMiddleware (đang là stub)"; `src/NewsCacheSession.Api/CLAUDE.md` đã ghi là xong từ 23/10 |

## 2. Sai lệch giữa SRS v2.0 và code

Cột "Đúng" lấy từ code. Đây là những gì bộ kiểm thử tài liệu ở Phase 2 phải bắt được.

| # | SRS v2.0 ghi | Đúng (bằng chứng) | Mức |
|---|---|---|---|
| D1 | Cookie `news_session` (`docs/SRS.md:173,304,339,344,351,360,730`) | Cookie `SessionId` (`src/NewsCacheSession.Api/Services/CurrentUserService.cs:17`) | Cao — sai khi demo F12 |
| D2 | `sessionId` dạng GUID hex `N` (`docs/SRS.md:331`) | `Guid.NewGuid().ToString()`, dạng `D` có gạch nối (`src/NewsCacheSession.Api/Controllers/AuthController.cs:141`) | Thấp |
| D3 | `username` tối thiểu 3 ký tự (`docs/SRS.md:319`) | Không có tối thiểu; `username` ≤ 50, `password` 6–72 (`src/NewsCacheSession.Api/DTOs/Auth/RegisterRequest.cs:8,13,14`) | Trung bình |
| D4 | `/api/cache/stats` trả `totalLookups, cacheHits, cacheMisses, hitRatio, uptimeSeconds` (`docs/SRS.md:592`) | `hits, misses, totalRequests, hitRate` (`src/NewsCacheSession.Api/Services/ICacheService.cs:5-8`; xác nhận bằng `scripts/Benchmark/results/2026-10-25-chinh-thuc/env.json` `cacheStatsBefore`) | Cao |
| D5 | Upload `POST /api/images/upload`, dùng Cloudinary .NET SDK (`docs/SRS.md:297,605`) | `POST /api/images` (`src/NewsCacheSession.Api/Controllers/ImagesController.cs:7,20`); gọi REST Cloudinary bằng `HttpClient` + chữ ký SHA1, không có SDK (`src/NewsCacheSession.Api/Services/CloudinaryImageStorageService.cs:64,111`; csproj không có gói Cloudinary) | Trung bình |
| D6 | RedisInsight `redislabs/redisinsight`, cổng `8001:5540`, mở `http://localhost:8001` (`docs/SRS.md:204,865`) | `redis/redisinsight:latest`, cổng `5540:5540` (`docker-compose.yml:26,30`) | Cao — demo bước 3 mở sai địa chỉ |
| D7 | `redis:7.0-alpine` (`docs/SRS.md:203`) | `redis:7-alpine`, có `--appendonly yes` (`docker-compose.yml:14,19`) | Thấp |
| D8 | `MongoDB.Driver` v2.28+, `StackExchange.Redis` v2.8+ (`docs/SRS.md:295,296`) | 3.11.0 và 3.1.13 (`src/NewsCacheSession.Api/NewsCacheSession.Api.csproj:12,13`) | Thấp |
| D9 | React 18, Vite 5 (`docs/SRS.md:123,206`) | React 19, Vite 8, Tailwind 4 (`src/frontend/package.json:18,33,34`) | Thấp |
| D10 | Trang chủ 10 bài/trang (`docs/SRS.md:275`) | `PAGE_SIZE = 12` (`src/frontend/src/pages/HomePage.jsx:7`); API mặc định 10, tối đa 50 | Thấp |
| D11 | Trang chủ có badge CACHE HIT/MISS (`docs/SRS.md:277`) | Chỉ `PostDetailPage.jsx` dùng `CacheStatusBadge` (grep `src/frontend/src/pages/*.jsx`) | Trung bình |
| D12 | File `CacheBadge.jsx` (`docs/SRS.md:829`) | `src/frontend/src/components/CacheStatusBadge.jsx` | Trung bình |
| D13 | Trùng slug thì "gắn hậu tố ngẫu nhiên" (`docs/SRS.md:381`) | Hậu tố tuần tự `-2, -3…` (`src/NewsCacheSession.Api/Controllers/PostsController.cs:550`); trùng khi insert thì thử lại, quá 3 lần trả 409 (`:50`, `:326-336`) | Thấp |
| D14 | Giải phóng lock bằng `WATCH … UNLINK/EXEC` (`docs/SRS.md:454`) | `LockReleaseAsync` của StackExchange.Redis (`src/NewsCacheSession.Api/Services/RedisCacheService.cs:95`) — giao dịch có điều kiện so token; lệnh xóa cụ thể phải xác nhận bằng `MONITOR` ở Phase 4, không viết `UNLINK` khi chưa thấy | Thấp |
| D15 | "49/49 Jira Tasks" hoàn thành (`docs/SRS.md:17`) | CSV có 37 ticket; 11 ticket chưa Done (SCRUM-33, 39–45, 47–49) | Cao — tự mâu thuẫn với chính nguồn |
| D16 | Stampede "4 đợt test" (`docs/SRS.md:619`) | 5 đợt, đều 1 MISS / 49 HIT / 0 lỗi (`summary.json` → `stampede[0..4]`) | Thấp |
| D17 | NFR-02 "Nhanh hơn 2.95× so với khi có cache hit" | Câu ngược nghĩa: HIT (2,96 ms) nhanh hơn MISS (8,74 ms) 2,95× | Trung bình |
| D18 | Demo B1 "MISS ~150–200 ms"; "tăng tốc gấp hàng chục lần" (`docs/SRS.md:851,853`) | Số đo thật: MISS 8,74 ms, HIT 2,96 ms, không cache 3,66 ms → HIT nhanh hơn không-cache 1,24×. Lý do đã có ở `docs/bao-cao-kiem-thu-hieu-nang.md` §5.2 | Cao — hội đồng hỏi là lộ |
| D19 | Redis dùng `volatile-lru` (`docs/SRS.md:714`) | Chỉ bản deploy Redis Cloud đặt `volatile-lru` (`plans/261025-1501-…/reports/06-deploy.md:8`); `docker-compose.yml` local không cấu hình `maxmemory` | Trung bình |
| D20 | HTTP/1.1 và HTTP/2 (`docs/SRS.md:301`) | Không có cấu hình HTTP/2 nào trong repo — phải bỏ hoặc ghi "theo mặc định Kestrel" sau khi kiểm | Thấp |
| D21 | Tăng lượt xem "< 1 ms" (`docs/SRS.md:543`) | Không có số đo nào cho `POST /view` | Thấp |
| D22 | "Clean Architecture" (`docs/SRS.md:122`) | Web API phân lớp Controller → Service, không có tầng Domain/Application tách riêng | Thấp |
| D23 | CSDL "tối thiểu 10.000 bài" (`docs/SRS.md:713`) | Đề bài chỉ yêu cầu ≥ 100. 10.150 là số thực đo (`env.json` `totalItems`), không phải yêu cầu | Trung bình |

## 3. SRS v2.0 thiếu

- `GET /api/auth/me` (`src/NewsCacheSession.Api/Controllers/AuthController.cs:181`) — trả `expiresInSeconds`.
- `GET /api/categories/{id}`, `GET /api/categories/slug/{slug}` (`src/NewsCacheSession.Api/Controllers/CategoriesController.cs:48,64`).
- Hai endpoint sức khỏe: `/health` (`src/NewsCacheSession.Api/Program.cs:83`) và `/api/health` (`src/NewsCacheSession.Api/Controllers/HealthController.cs:7`, trả 503 khi không Healthy).
- Cờ `PostingSettings:AdminOnly` (`src/NewsCacheSession.Api/appsettings.json:20`, `Services/PostingPolicy.cs`) — bản deploy chỉ admin đăng bài/tải ảnh.
- Cache danh sách dùng `all` khi không lọc chuyên mục và coi là MISS khi `pageSize` lệch bản cache (`src/NewsCacheSession.Api/Controllers/PostsController.cs` `GetAll`). `GET /api/posts` cũng gắn header `X-Cache`.
- Thu hồi phiên: không tự thu hồi phiên đang dùng (400), phiên không tồn tại (404); liệt kê tối đa 200 phiên, SCAN `pageSize: 100` (`AuthController.cs:236`, `Services/RedisSessionQueryService.cs`).
- Redis sập: middleware coi request như khách, endpoint cần Redis trả 503 (`src/NewsCacheSession.Api/Middleware/RedisUnavailableMiddleware.cs`).
- Môi trường deploy (Render + MongoDB Atlas M0 + Redis Cloud + Vercel) — `docs/huong-dan-deploy.md`.
- Lệch TargetFramework: test `net10.0`, API `net8.0` (`tests/NewsCacheSession.Tests/NewsCacheSession.Tests.csproj:4`). Lệnh kiểm thử trong SRS phải ghi rõ cần SDK 10.

## 4. Mâu thuẫn trong chính tài liệu nguồn

| # | Mâu thuẫn | Cách SRS v3 xử lý |
|---|---|---|
| S1 | Đề bài: "lần 1 ~200ms vs lần 2 <5ms". Thực đo: 8,74 ms vs 2,96 ms | Ghi yêu cầu đúng nguyên văn, tiêu chí chấp nhận đo được (HIT ≤ 5 ms, HIT < MISS, header `X-Cache` đổi MISS → HIT), dẫn §5.2 báo cáo hiệu năng |
| S2 | Đề bài: SV2 làm "Middleware Cache-Aside". Code: Cache-Aside nằm trong `PostsController.GetById`, không phải middleware | Ghi rõ quyết định thiết kế và lý do (chỉ một endpoint được cache, endpoint slug cố ý không cache) |
| S3 | Đề bài: "Strings/Hashes cho Cache bài viết" — mở. Code chọn String JSON | Ghi lựa chọn + lý do (`docs/redis-keyspace.md` "Vì sao chọn cấu trúc dữ liệu") |
| S4 | Đề bài: "20–50 Session/Cache Keys" — không rõ là khoảng hay mức tối thiểu | Diễn giải: ≥ 20 key có TTL, TTL khác nhau. Seed tạo 40 hoặc 50 key, mặc định 40 = 20 phiên TTL rải 300→1800 s + 20 cache bài TTL ≤ 600 s (`scripts/SeedRedis/seed_redis.py:91,97,255`) |
| S5 | CSV: SCRUM-24 ghi `SET NX PX`; keyspace ghi `NX EX 5`; checklist ghi `NX PX 5000` | Một yêu cầu: khóa có TTL 5 giây, cấp bằng `SET … NX` + hết hạn. Đơn vị gửi đi xác nhận bằng `MONITOR` ở Phase 4 |
| S6 | CSV: Sprint 1 "23 Sep – 24 Sep" chồng lên Sprint 2 "23 Sep – 29 Sep" | Ghi vào phụ lục "vấn đề tài liệu nguồn", không sửa CSV (xuất từ Jira) |
| S7 | CSV: SCRUM-39–45, 47–49 là Idea/In Progress nhưng repo đã có sản phẩm (upload ảnh, benchmark, biểu đồ, báo cáo hiệu năng, deploy SCRUM-43) | Ma trận truy vết có hai cột: "Trạng thái CSV" và "Bằng chứng trong repo" |
| S8 | Đề bài: "MongoDB / MySQL" làm DB gốc | Ghi lựa chọn MongoDB |
| S9 | `AGENTS.md` §6, `docs/checklist-barem.md` lạc hậu (xem §1) | Không sửa — gửi báo cáo cho chủ sở hữu ở Phase 4 |

## 5. Bằng chứng kiểm thử hiện có (để ghép vào ma trận TC)

Test .NET (`tests/NewsCacheSession.Tests/`): 13 file. Integration test cần `NEWS_IT=1` và stack QA.
Đã liệt kê tên từng test method trong lúc scout. Những test dùng làm bằng chứng chính:

| Yêu cầu | Test |
|---|---|
| Đăng ký, admin đầu tiên, BCrypt, trùng username | `Integration/AuthFlowTests.cs` (10 test) |
| Session Hash 5 field, TTL, sliding, cookie, hết hạn, thu hồi | `Integration/SessionLifecycleTests.cs`, `Integration/SessionExpiryTests.cs`, `Middleware/SessionAuthMiddlewareTests.cs`, `Services/SessionServiceTests.cs` |
| CRUD bài viết, phân quyền, slug, xóa mềm, phân trang | `Integration/PostCrudFlowTests.cs` |
| Cache-Aside, invalidation, slug không cache, stampede 50 luồng | `Integration/CacheInvalidationTests.cs`, `Controllers/PostsControllerCacheAsideTests.cs` |
| INCR, flush, dirty set, thống kê hit/miss | `Integration/ViewCounterFlowTests.cs`, `Services/ViewCountSyncTests.cs`, `Services/CacheServiceTests.cs` |
| Redis sập, lock kẹt, Cloudinary chậm, Mongo lỗi khi flush | `Integration/ResilienceTests.cs` |
| Health | `Integration/HealthEndpointTests.cs` |

Frontend: Vitest (`src/frontend/src/**/*.test.jsx`). Script Python: `unittest` (`scripts/*/test_*.py`).
Không có `pytest` trên máy — bộ kiểm thử tài liệu phải dùng `unittest` thư viện chuẩn.
