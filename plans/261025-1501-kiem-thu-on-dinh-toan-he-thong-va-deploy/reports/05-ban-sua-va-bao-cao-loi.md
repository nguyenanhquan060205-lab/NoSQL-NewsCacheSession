# Phase 5 — Bản sửa và báo cáo lỗi (26/10/2026)

## Đã sửa — file của SV2 (Quân), trên `develop`

Mỗi bản sửa một commit, có test đỏ trước (commit `f98443b`, `d5d1bd3`), xanh sau.

| # | Lỗi | Commit | Test chứng minh |
|---|---|---|---|
| S1 | G9 — Redis sập: mọi request treo ~6 s rồi 500 | `49706a5` | `ResilienceTests.RedisDown_…` ✅; chạy lại `docker stop news-redis-qa` trên API QA: đọc bài 200 trong 3–15 ms, tạo bài/đăng nhập/lượt xem 503 trong 8–176 ms, Redis lên lại tự hồi phục sau ~1,75 s |
| S2 | G10 — đệ quy chờ lock | `49706a5` | `ResilienceTests.GetById_WhileAnotherHolderKeepsLock_…` ✅; trên API QA: 5,04 s → **2,11 s**, không ghi cache khi đọc thẳng Mongo |
| S3 | G11 — worker mất ID khi Mongo lỗi | `7ecc3d5` | `ResilienceTests.Flush_WhenMongoWriteFails_…` ✅ |
| S4 | G17 (ý cookie) — cookie không trượt | `43b1aa5` | `SessionLifecycleTests.Request_WithCookieAfterSliding_…` ✅; đăng xuất vẫn xóa được cookie |
| G18 (ý SV2) | HSET + EXPIRE rời nhau | `8d7488a` | `SessionServiceTests.CreateSessionAsync_…InOneTransaction` ✅ |
| S5 | JSON cache phình 36–40 % | `cd71517` | Bài dài nhất `MEMORY USAGE` 655 432 → **393 288 B**; body MISS = HIT; `CacheInvalidationTests` ✅ |

Thiết kế S1 khác plan một chỗ: **không phải sửa `Program.cs`** — `RedisUnavailableMiddleware` được đăng ký
bên trong `UseSessionAuth()` (file SV2), đúng vị trí plan yêu cầu (ngay sau `UseCors()`, trước middleware
phiên). Thêm `RedisAvailability.EnsureConnected` kiểm `IsConnected` trước mỗi lệnh vì Phase 4 đo được
backlog chờ 5 s; nếu chỉ bắt exception thì trang chủ vẫn treo ~15 s khi Redis sập.

Đánh đổi đã chấp nhận (ghi vào phản biện): khi Redis vừa chập chờn (đang kết nối lại), request trong
khoảng đó coi như MISS / trả 503 thay vì chờ; `RemoveAsync` lỗi thì bản cache cũ sống tối đa hết TTL 10 phút.

Cổng hồi quy sau bản sửa cuối:
```
dotnet build (API)            0 Warning(s), 0 Error(s)
dotnet test                   30 pass, 43 skipped
NEWS_IT=1 dotnet test         67 pass, 6 fail — cả 6 nằm trong file của SV1 (bảng dưới)
vitest / oxlint / build       103/103 · exit 0 · OK
E2E Phase 3                   12/12
```

Kèm theo: `scripts/Smoke/smoke_test.py` (`46098a7`) — 9/9 bước xanh trên API QA.

## Không sửa

| # | Lý do |
|---|---|
| G12 đếm lượt xem bài đã xóa | Đánh đổi hiệu năng đã chốt; có test ghi lại hành vi |
| D1 test SeedRedis | Không phải lỗi code — Python hệ thống thiếu `bson` (Phase 1) |
| D2 banner bài mẫu | Phase 3 kết luận banner đủ rõ |
| MongoDB sập → treo 30 s | Không phải lỗi code; đặt `serverSelectionTimeoutMS=5000` trong chuỗi kết nối deploy |

## Đã sửa — file của Như, Định và file dùng chung (sau khi nhóm đồng ý)

| # | Lỗi | Commit | Test chứng minh |
|---|---|---|---|
| N1 | G15 — 9/10 request tạo bài cùng tiêu đề trả 500 | `d25252e` | `PostCrudFlowTests.Create_TenParallelPostsWithSameTitle_…` ✅ (chỉ 201/409, slug không trùng) |
| N2 | G14 — cache cũ sống trong lúc chờ Cloudinary | `fc09aee` | `ResilienceTests.Update_WhileCloudinaryIsSlow_…` ✅ |
| N3 | G16 — 10/10 đăng ký song song thành admin | `9cbb6fe` | `AuthFlowTests.Register_TenParallelFirstRegistrations_…` ✅ (đúng 1 admin) |
| N4 | G17/G18 — TTL hardcode, ghi phiên 2 bước | `5c0a4b0` | `SessionLifecycleTests.Login_WithConfiguredTtl_…` ✅ (TTL 15 phút → Hash 900 s, cookie `Max-Age=900`) |
| N5 | G19 — không giới hạn độ dài | `6631674` | `Create_OverlongTitle_…`, `Register_OverlongUsernameOrPassword_…` ✅ |
| N6 | G28 — doc keyspace lệch code | `4c9a9c9` | Đối chiếu `MONITOR`: lock là `SET <token> NX EX 5`, giải phóng bằng `WATCH/GET/MULTI/UNLINK/EXEC` (không phải Lua như ghi chú cũ) |
| S5b | JSON cache danh sách | `d2bcb27` | `CacheInvalidationTests.GetAll_…`, `PostCrudFlowTests.GetAll_…` ✅ |
| D3 | Cloudinary chờ tới 100 s | `89218f2` | `CloudinaryImageStorageServiceTests.Constructor_ShouldCapHttpTimeoutAt15Seconds` ✅ |
| README | Mục test, SDK 10, Mongo Homebrew | `d33f94d` | — |
| (phụ) | Tên unit test ghi sai cơ chế giải phóng lock | `5ef3e56` | — |

Cổng hồi quy sau commit cuối (`d33f94d`):
```
dotnet build (API)            0 Warning(s), 0 Error(s)
dotnet test                   31 pass, 43 skipped
NEWS_IT=1 dotnet test         74/74 pass
vitest / oxlint / build       103/103 · exit 0 · OK
```
Diễn tập lại trên stack demo chạy `develop` mới nhất: 2 lượt × 3 bước đều đạt (`03-e2e-va-dien-tap.md`).

Chưa làm trong phạm vi được duyệt: `CLAUDE.md` ở gốc repo và `src/NewsCacheSession.Api/CLAUDE.md` vẫn ghi lock
là `SET … 1 NX PX 5000` và chưa có `posts:dirty_views` — hai file hướng dẫn agent này không nằm trong danh sách
N6; báo nhóm để ai sở hữu sửa.

## Tin nhắn gửi nhóm

```text
Mình (Quân) vừa chạy kiểm thử toàn hệ thống trên môi trường QA riêng (Redis + MongoDB thật,
không đụng dữ liệu demo). Phần của mình đã sửa xong trên nhánh develop. Còn mấy lỗi nằm trong
file của Như và Định, mình xin phép sửa giúp (mỗi lỗi một commit nhỏ, có test chứng minh):

@Như — Controllers/PostsController.cs (Create/Update/Delete/GetAll), AuthController.cs, DTOs, docs:
 N1. Tạo 10 bài cùng tiêu đề cùng lúc thì 9 bài trả lỗi 500 (unique index slug chặn nhưng code không bắt).
     → bắt DuplicateKey, sinh lại slug, thử tối đa 3 lần, vẫn trùng thì 409.
 N2. Sửa/xóa bài có ảnh: gọi Cloudinary TRƯỚC khi xóa cache → Cloudinary chậm thì cache cũ còn sống.
     → đổi thứ tự: ghi Mongo → xóa cache → rồi mới xóa ảnh cũ.
 N3. 10 người đăng ký đầu tiên cùng lúc thì cả 10 thành admin (deploy công khai rất nguy hiểm).
     → giành quyền admin bằng một lệnh insert {_id:"bootstrapAdmin"} vào collection meta.
 N4. TTL phiên hardcode 30 phút, bỏ qua SessionSettings:TtlMinutes; ghi phiên 2 bước.
     → đọc từ config, gọi CreateSessionAsync có tham số role.
 N5. Không giới hạn độ dài: tiêu đề 301 ký tự, username 51 ký tự, mật khẩu 73 byte đều qua.
     → [MaxLength]: tiêu đề 300, nội dung 500 000, username 50, mật khẩu 6–72.
 N6. docs/redis-keyspace.md thiếu key posts:dirty_views và ghi lệnh lock khác code thật
     (thầy đối chiếu doc với RedisInsight — barem 1.5đ). → bổ sung doc + bảng trong AGENTS.md.
 S5b. Cache danh sách lưu JSON escape tiếng Việt (\uXXXX), phình ~40% → giữ nguyên chữ có dấu.

@Định — Services/CloudinaryImageStorageService.cs + chuẩn bị deploy:
 D3. HttpClient gọi Cloudinary dùng timeout mặc định 100 giây → đặt 15 giây.
 Deploy: thêm src/frontend/vercel.json (rewrite /api sang Render + F5 trang con không 404).

@Cả nhóm — file dùng chung:
 README.md: thêm cách chạy integration test (NEWS_IT=1) và ghi chú Mongo Homebrew chiếm cổng 27017 trên macOS;
 thêm Dockerfile + .dockerignore ở gốc repo để deploy Render.
 (Program.cs KHÔNG cần sửa.)

Bằng chứng (lệnh + output) ở plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/reports/.
Mọi người đồng ý mục nào thì trả lời số mục giúp mình nhé. Mục nào không đồng ý mình chỉ gửi báo cáo lỗi.
```

## Ai đồng ý mục nào

26/10/2026 — Quân xác nhận nhóm **đồng ý tất cả**: N1–N6, S5b (Như); D3 + `vercel.json` (Định);
`README.md`, `Dockerfile`, `.dockerignore` (cả nhóm). Không mục nào chuyển thành báo cáo lỗi.
