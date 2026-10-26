---
phase: 5
title: "Sửa lỗi theo chủ sở hữu và đưa develop lên main"
status: pending
priority: P1
effort: "6h"
dependencies: [2, 3, 4]
---

# Phase 5: Sửa lỗi theo chủ sở hữu và đưa `develop` lên `main`

## Goal
Sửa mọi lỗi đã được Phase 2–4 **chứng minh** (không sửa giả thuyết chưa có bằng chứng), mỗi bản
sửa có test đỏ trước, xanh sau; rồi đưa `develop` lên `main` qua Pull Request.

## Quy tắc (đã chốt với bạn — phương án B)
- File của bạn (SV2): sửa thẳng.
- File của Như (SV1) / Định (SV3) / file dùng chung: **nhắn nhóm xin phép trước**, ghi rõ file và
  lý do; chỉ sửa sau khi được đồng ý. Lỗi nhỏ không chặn gì thì chỉ gửi báo cáo cho chủ file.
- Mỗi bản sửa một commit trên `develop`, tiếng Việt, mã ticket gốc, **không** có `Co-Authored-By`.

## Scout pass trước khi làm
Đọc `reports/02-*.md`, `reports/03-*.md`, `reports/04-*.md`; bỏ khỏi danh sách dưới đây mọi mục
mà báo cáo kết luận "giả thuyết sai".

## Danh sách sửa dự kiến (chỉ làm mục đã được chứng minh)

### File của bạn (SV2)

| # | Lỗi | Hướng sửa | File | Ticket |
|---|---|---|---|---|
| S1 | G9 Redis chết → cả API 500 | `RedisCacheService`: `GetAsync` lỗi kết nối/timeout → trả `null` (coi như MISS) và log; `SetAsync`/`RemoveAsync` lỗi → log mức Error rồi bỏ qua (bản cũ tự hết hạn theo TTL 10 phút). `IncrementAsync` vẫn ném lỗi vì bộ đếm cần giá trị thật. `SessionAuthMiddleware`: Redis lỗi → coi như chưa đăng nhập, log cảnh báo. Thêm middleware mới đổi `RedisConnectionException`/`RedisTimeoutException` thành **503** JSON tiếng Việt cho các endpoint cần phiên; đăng ký ngay sau `UseCors()` và **trước** `UseSessionAuth()` để bọc được cả middleware phiên lẫn controller. | `Services/RedisCacheService.cs`, `Middleware/SessionAuthMiddleware.cs`, `Middleware/RedisUnavailableMiddleware.cs` (mới), `Program.cs` (1 dòng đăng ký — file dùng chung, xin phép) | SCRUM-20, SCRUM-15 |
| S2 | G10 đệ quy chờ lock | Thay đệ quy bằng vòng chờ có giới hạn (ví dụ 40 × 50ms); hết lượt thì đọc thẳng MongoDB, không ghi cache. Lấy lock bị lỗi Redis → đọc thẳng MongoDB. **Làm cùng S1.** | `Controllers/PostsController.cs` (GetById) | SCRUM-24 |
| S3 | G11 worker mất ID khi Mongo lỗi | Bắt lỗi từng bài; lỗi thì `MarkDirtyViewAsync` lại ID đó | `Services/ViewCountSyncWorker.cs` | SCRUM-25 |
| S4 | G17 cookie không trượt | Middleware cấp lại cookie `SessionId` (cùng `HttpOnly`, `SameSite=Lax`, `Secure` theo scheme, `MaxAge` = TTL) mỗi lần gia hạn — chỉ khi phiên đến từ cookie, không phải header | `Middleware/SessionAuthMiddleware.cs` | SCRUM-15 |
| S5 | JSON cache phình to + khó đọc trên RedisInsight | Serialize cache bằng `JavaScriptEncoder.UnsafeRelaxedJsonEscaping` (giữ tên field để đọc được key cũ). Đo `MEMORY USAGE` trước/sau. Phần `GetAll` nằm trong vùng của Như → xin phép. | `Controllers/PostsController.cs` | SCRUM-21, SCRUM-26 |
| — | G12 đếm lượt xem bài đã xóa | **Không sửa** — ghi vào câu trả lời phản biện (đánh đổi hiệu năng) | — | — |

### File của Như (SV1) — xin phép trước

| # | Lỗi | Hướng sửa | File | Ticket |
|---|---|---|---|---|
| N1 | G15 tạo bài cùng tiêu đề song song → 500 | Bắt `DuplicateKey` của `ux_posts_slug`, sinh lại slug và thử tối đa 3 lần, vẫn trùng thì 409 | `Controllers/PostsController.cs` (Create) | SCRUM-16 |
| N2 | G14 Cloudinary chặn invalidation | Đổi thứ tự: ghi Mongo → xóa cache + `INCR posts:ver` → rồi mới xóa ảnh cũ | `Controllers/PostsController.cs` (Update, Delete) | SCRUM-23 |
| N3 | G16 hai admin khi đăng ký đầu tiên song song | Giành quyền admin bằng một lệnh nguyên tử: insert document `{_id: "bootstrapAdmin"}` vào collection `meta`; ai insert được thì là admin, `DuplicateKey` thì là user. Cập nhật `docs/mongodb-schema.md`. (Không dùng partial unique index vì DB demo đã có 2 admin.) | `Controllers/AuthController.cs`, `docs/mongodb-schema.md` | SCRUM-13 |
| N4 | G17 TTL hardcode + G18 ghi phiên 2 bước | Đọc `SessionSettings:TtlMinutes` cho cả phiên và cookie; gọi overload `CreateSessionAsync(..., role, ttl)` đã có sẵn thay cho tạo phiên rồi `TouchAsync` | `Controllers/AuthController.cs` | SCRUM-13, SCRUM-14 |
| N5 | G19 không giới hạn độ dài | `[MaxLength]`: Title 300 (dài nhất hiện có 110), Content 500 000 (dài nhất 275 018), Username 50, Password 6–72 | `DTOs/Posts/*.cs`, `DTOs/Auth/RegisterRequest.cs` | SCRUM-16, SCRUM-13 |
| N6 | G28 doc keyspace thiếu `posts:dirty_views` | Thêm dòng `posts:dirty_views` (Set, không TTL) vào bảng; sửa giá trị lock thành token ngẫu nhiên; đồng bộ bảng trong `AGENTS.md` | `docs/redis-keyspace.md`, `AGENTS.md` | SCRUM-33 |

### File của Định (SV3) — xin phép trước

| # | Lỗi | Hướng sửa | File | Ticket |
|---|---|---|---|---|
| D1 | G5 test SeedRedis fail | Sửa theo kết luận Phase 1/3 (code sai thì sửa script, test sai thì sửa test) | `scripts/SeedRedis/*` | SCRUM-36 |
| D2 | G20 bài mẫu giả che lỗi API | Chỉ sửa nếu Phase 3 thấy banner không đủ rõ: làm banner nổi bật và ghi rõ "API không phản hồi" | `src/frontend/src/pages/HomePage.jsx` (+ test) | SCRUM-22 |
| D3 | Cloudinary treo tới 100s | Đặt `HttpClient.Timeout` 15s cho service ảnh | `Services/CloudinaryImageStorageService.cs` | SCRUM-39 |

### File dùng chung — hỏi cả nhóm
- `Program.cs`: đăng ký middleware của S1.
- `README.md`: mục Test (cần .NET SDK 10, cách chạy integration test với `NEWS_IT=1`), ghi chú
  xung đột Mongo Homebrew trên macOS.

## Tests Before
Với mỗi mục: chỉ ra test đỏ tương ứng từ Phase 2/4 (tên test). Mục nào chưa có test đỏ thì viết test trước rồi mới sửa.

## Implementation Steps
1. Gửi nhóm một tin nhắn duy nhất liệt kê N1–N6, D1–D3 và phần file dùng chung, kèm bằng chứng từ báo cáo. Chờ trả lời.
2. Sửa S1+S2 trước (cùng nhau), rồi S3, S4, S5.
3. Sửa các mục được Như/Định đồng ý; mục bị từ chối chuyển thành báo cáo lỗi gửi chủ file.
4. Sau mỗi bản sửa: chạy cổng hồi quy bên dưới rồi mới commit.
5. Chạy lại các kịch bản dừng container của Phase 4 (Redis/Mongo chết) để xác nhận hành vi mới.
6. Ghi `reports/05-ban-sua-va-bao-cao-loi.md`: bản sửa nào, commit nào, test nào; báo cáo lỗi còn tồn cho từng người.
7. Đẩy `develop` lên GitHub và mở PR `develop → main` (**hỏi bạn trước khi push**). Merge xong mới sang Phase 6.

## Refactor
Chỉ thay đổi nằm trong các hàng ở bảng trên. Không đổi keyspace, tên field MongoDB hay hợp đồng API.

## Tests After / Regression gate (chạy sau MỖI bản sửa)
```bash
dotnet build src/NewsCacheSession.Api/NewsCacheSession.Api.csproj
dotnet test
NEWS_IT=1 dotnet test
cd src/frontend && npx vitest run && npx oxlint && npm run build
```
Cuối phase: diễn tập lại 3 bước demo một lượt trên stack demo (Phase 3 Phần C, bước 5).

## Dependency map
- Đầu vào: báo cáo Phase 2, 3, 4.
- Đầu ra: `main` đã có mọi bản sửa → Phase 6 deploy từ `main`.

## Success Criteria
- Mọi test đỏ có trong báo cáo đều xanh, hoặc đã chuyển thành báo cáo lỗi kèm lý do.
- Redis chết: trang chủ và trang chi tiết vẫn đọc được từ MongoDB; thao tác cần phiên trả 503 rõ ràng; `/health` báo Unhealthy.
- PR `develop → main` đã merge, CI/`dotnet test` trên `main` sạch.

## Risk Assessment
- S1 nuốt lỗi `RemoveAsync` → khi Redis vừa sống lại có thể còn bản cache cũ tối đa 10 phút. Chấp nhận, ghi vào phản biện.
- Đụng file người khác gây conflict → mỗi bản sửa nhỏ, báo nhóm trước khi push, rebase `develop` trên `main` mới nhất trước khi mở PR.
- Sửa sát ngày demo → diễn tập lại sau khi sửa (Tests After).

## Security Considerations
- N3 khóa lỗ hổng "người đăng ký đầu tiên thành admin" khi chen nhau — quan trọng trước khi deploy công khai.
- N5 chặn payload quá lớn và giới hạn BCrypt 72 byte.

## Todo
- [x] Gửi nhóm danh sách N1–N6, D1–D3, file dùng chung kèm bằng chứng; ghi lại ai đồng ý mục nào
- [x] S1 + S2: Redis lỗi → đọc thẳng MongoDB, 503 cho thao tác cần phiên, vòng chờ lock có giới hạn
- [x] S3, S4, S5
- [x] Các mục của Như/Định đã được đồng ý
- [x] Chạy lại kịch bản dừng container của Phase 4
- [x] Ghi `reports/05-ban-sua-va-bao-cao-loi.md`
- [ ] Hỏi rồi push `develop`, mở PR `develop → main`, merge
