---
phase: 2
title: "Integration test backend thật (flow Như + Quân)"
status: pending
priority: P1
effort: "5h"
dependencies: [1]
---

# Phase 2: Integration test backend thật (flow Như + Quân)

## Goal
Thay bằng chứng "mock gọi mock" bằng test đi qua HTTP thật → controller → Redis/MongoDB thật,
phủ toàn bộ flow API của SV1 và SV2, và ghi kết luận đúng/sai cho G8–G19.

## Scout pass trước khi làm (bắt buộc với `--deep`)
- Đọc lại `tests/NewsCacheSession.Tests/**` và `Program.cs` trên nhánh `develop`.
- Xác nhận container QA từ Phase 1 còn chạy: `docker ps --filter name=news-.*-qa`.

## Key Insights
- `Program.cs:33-36` đọc chuỗi kết nối Redis **trước** `builder.Build()` → đè cấu hình qua
  `ConfigureAppConfiguration` có thể không kịp. Dùng biến môi trường đặt trong constructor của
  factory (`RedisSettings__ConnectionString`, `MongoSettings__*`) — chắc chắn được đọc.
- Không cần sửa `Program.cs` (file dùng chung): `WebApplicationFactory<T>` chỉ cần một kiểu public
  bất kỳ trong assembly API, ví dụ `HealthController`. Spike ở bước 1 xác nhận điều này.
- `RedisSessionQueryService` SCAN theo `db.Database` → chạy đúng với `defaultDatabase=15`.
- Client của factory mặc định giữ cookie; `Request.IsHttps=false` nên cookie không có `Secure` → gửi lại được.
- Hosted service (`MongoIndexInitializer`, `ViewCountSyncWorker`) chạy thật trong test → index
  unique được tạo trên DB test, đúng điều cần kiểm tra ở G15.

## An toàn dữ liệu (chặn cứng trong code test)
- Mongo: DB tên `newsdb_it_{guid}`, drop khi xong. Factory **ném lỗi** nếu tên DB không bắt đầu bằng `newsdb_it_`.
- Redis: chỉ DB 15, `FLUSHDB` trước mỗi lớp test bằng kết nối riêng `allowAdmin=true`. Factory **ném lỗi** nếu chỉ số DB khác 15.
- Chạy test chỉ khi `NEWS_IT=1`; chuỗi kết nối lấy từ `NEWS_IT_MONGO` (mặc định `mongodb://localhost:27019`)
  và `NEWS_IT_REDIS` (mặc định `localhost:6380`) — tức container QA, không bao giờ là stack demo.

## File inventory

| File | Hành động | Cỡ | Ảnh hưởng test |
|---|---|---|---|
| `tests/NewsCacheSession.Tests/NewsCacheSession.Tests.csproj` | Sửa: thêm `Microsoft.AspNetCore.Mvc.Testing` | +1 dòng | Bật WebApplicationFactory |
| `tests/.../Integration/Infrastructure/NewsApiFactory.cs` | Tạo | ~120 dòng | Factory + chặn an toàn + helper đăng ký/đăng nhập |
| `tests/.../Integration/Infrastructure/IntegrationFactAttribute.cs` | Tạo | ~20 dòng | Bỏ qua test khi thiếu `NEWS_IT=1` |
| `tests/.../Integration/AuthFlowTests.cs` | Tạo | ~150 dòng | Flow SV1 đăng ký/đăng nhập |
| `tests/.../Integration/PostCrudFlowTests.cs` | Tạo | ~200 dòng | Flow SV1 CRUD + phân quyền |
| `tests/.../Integration/CacheInvalidationTests.cs` | **Viết lại** (G8) | ~150 dòng | Cache-Aside + invalidation thật |
| `tests/.../Integration/SessionLifecycleTests.cs` | Tạo | ~150 dòng | Session Hash, sliding, hết hạn, thu hồi |
| `tests/.../Integration/ViewCounterFlowTests.cs` | Tạo | ~120 dòng | INCR + write-behind |

Thư mục `tests/` do SV2 dựng (SCRUM-35, SCRUM-37) → thuộc phần của bạn.

## Tests Before (viết trước, chạy để thấy đỏ/xanh — đây là bước "chẩn đoán")

### Flow Như (SV1)

| Mức | Test | Kỳ vọng đúng |
|---|---|---|
| Critical | Đăng ký user đầu tiên | 201, `role=admin`; user thứ hai `role=user` |
| Critical | Đăng nhập đúng | 200, có cookie `SessionId` (HttpOnly), body có `sessionId` |
| Critical | Sai mật khẩu / sai username | Cùng 401, cùng thông báo |
| High | Trùng username | 409 |
| High | `GET /api/auth/me` sau đăng nhập / sau đăng xuất | 200 có `expiresInSeconds≈1800` / 401 |
| Critical | Tạo bài khi chưa đăng nhập | 401 |
| Critical | Tạo bài có `categoryId` hợp lệ | 201, slug tiếng Việt không dấu, Mongo lưu `categoryId` dạng ObjectId |
| High | `categoryId` sai cú pháp / không tồn tại | 400 |
| High | Tạo 2 bài cùng tiêu đề tuần tự | slug `-2` |
| High | **10 request tạo bài cùng tiêu đề song song (G15)** | Không request nào 500 |
| Critical | User thường sửa/xóa bài seed (`authorId=null`) | 403, cache bài giữ nguyên |
| Critical | Tác giả sửa bài mình / admin sửa bài bất kỳ | 200 |
| High | Xóa mềm | 204 → `GET` 404, Mongo `isDeleted=true`, `deletedAt` có giá trị |
| High | Danh sách: phân trang, lọc chuyên mục, `pageSize>50` | Đúng số bài, kẹp về 50 |
| Medium | **10 request đăng ký đầu tiên song song trên DB rỗng (G16)** | Đúng **1** admin |

### Flow Quân (SV2)

| Mức | Test | Kỳ vọng đúng |
|---|---|---|
| Critical | `GET /api/posts/{id}` lần 1 rồi lần 2 | `X-Cache: MISS` → `HIT`; `post:{id}` là String, TTL 1–600 |
| Critical | Sửa bài → key `post:{id}` | Bị xóa ngay sau PUT; `posts:ver` tăng 1; GET kế tiếp MISS với tiêu đề mới |
| Critical | Xóa mềm → key `post:{id}` | Bị xóa; `post:{id}:views` **được giữ** |
| High | `GET /api/posts/slug/{slug}` | Không tạo key `post:*` (cố ý không cache) |
| High | Danh sách: gọi 2 lần → tạo bài → gọi lại | HIT → MISS và bài mới đứng đầu |
| High | Stampede: 50 request song song vào bài chưa cache | Đúng 1 MISS, 49 HIT, không còn key `lock:post:{id}` |
| Critical | Session Hash sau đăng nhập | Đủ `userId, username, role, loginAt, lastActive`; TTL ≤ 1800 |
| Critical | Sliding: hạ TTL còn 100s bằng `EXPIRE`, gọi 1 request có cookie | TTL quay về ≈1800, `lastActive` đổi |
| Critical | Hết hạn: `EXPIRE session:{id} 1`, chờ 2s | Request kế tiếp 401, **không** tạo lại Hash mồ côi |
| High | Admin thu hồi phiên user / tự thu hồi mình / user thường gọi | 204 rồi user bị 401 / 400 / 403 |
| High | `GET /api/auth/sessions` với 3 phiên | Đủ 3 phiên kèm TTL |
| Critical | Bài có `views=500` trong Mongo, Redis chưa có key đếm → 1 lượt xem | Trả 501 (bản sửa G13) |
| High | 50 lượt xem song song | Tăng đúng 50 |
| High | Lượt xem ID không tồn tại | 404, không tạo key |
| High | Gọi `ViewCountSyncWorker.FlushViewsToMongoAsync` | Mongo `views` = Redis; `posts:dirty_views` rỗng |
| Medium | `GET /api/cache/stats` sau 1 MISS + 1 HIT | `hits` và `misses` mỗi loại tăng 1 |

## Implementation Steps
1. **Spike (≤30 phút):** thêm `Microsoft.AspNetCore.Mvc.Testing` (thử bản khớp runtime test
   `net10.0`; lỗi thì thử bản 8.0.x), viết 1 test `GET /health` qua `NewsApiFactory`. Nếu factory
   không khởi động được mà không sửa `Program.cs` → dừng, hỏi nhóm cho phép thêm `public partial class Program {}`.
2. Viết `NewsApiFactory` + `IntegrationFactAttribute` với các chặn an toàn ở trên; **mọi** lớp
   integration dùng chung một `[Collection("Integration")]` để chạy tuần tự (biến môi trường là của
   cả tiến trình, hai collection chạy song song sẽ ghi đè nhau). Test "đăng ký đầu tiên song song"
   (G16) cần DB rỗng → tạo factory thứ hai với DB `newsdb_it_{guid}` riêng **bên trong** collection
   đó, dispose xong mới sang test khác.
3. Viết lần lượt 5 file test theo hai bảng trên. Seed dữ liệu tối thiểu trong test (2 chuyên mục,
   3 bài, 1 bài `views=500`), không phụ thuộc `newsdb`.
4. Chạy: `NEWS_IT=1 dotnet test --filter "FullyQualifiedName~Integration"`.
5. Ghi `reports/02-ket-qua-integration.md`: mỗi test đỏ → giả thuyết nào, bằng chứng (output),
   chủ sở hữu. **Không sửa code sản phẩm ở phase này** — sửa ở Phase 5 để test đỏ còn làm bằng chứng.

## Refactor
Không đổi code sản phẩm. Chỉ viết lại `CacheInvalidationTests.cs` (test giả → test thật).

## Tests After / Regression gate
- `dotnet test` (không `NEWS_IT`) → mọi test cũ xanh, test integration báo Skipped, không cần Docker.
- `NEWS_IT=1 dotnet test` → test xanh = hành vi đúng; test đỏ đã có trong báo cáo kèm giả thuyết.

## Dependency map
- Cần Phase 1 (container QA, nhánh `develop`).
- Test đỏ ở đây là đầu vào của Phase 5; test xanh là cổng hồi quy cho Phase 5 và Phase 6.

## Success Criteria
- Có ít nhất 1 test cho mỗi dòng trong hai bảng.
- Mỗi giả thuyết G8–G19 có kết luận đúng/sai trong `reports/02-ket-qua-integration.md`.

## Risk Assessment
- Mvc.Testing lệch phiên bản giữa test `net10.0` và API `net8.0` → spike ở bước 1.
- Test liên quan thời gian (TTL) chập chờn → dùng `EXPIRE` ngắn + chờ có giới hạn, không `sleep` 30 phút.
- Worker flush chạy nền mỗi phút có thể chen vào test lượt xem → gọi `FlushViewsToMongoAsync` trực tiếp và kiểm tra theo giá trị cuối.

## Security Considerations
Mật khẩu test sinh ngẫu nhiên trong test, không ghi ra file.

## Todo
- [x] Spike `Microsoft.AspNetCore.Mvc.Testing` + test `/health` qua factory
- [x] `NewsApiFactory` + `IntegrationFactAttribute` có chặn an toàn DB/Redis
- [x] `AuthFlowTests` (flow Như)
- [x] `PostCrudFlowTests` (flow Như, gồm G15, G16)
- [x] Viết lại `CacheInvalidationTests` thành test thật (G8)
- [x] `SessionLifecycleTests` (flow Quân)
- [x] `ViewCounterFlowTests` (flow Quân)
- [x] Ghi `reports/02-ket-qua-integration.md` với kết luận G8–G19
