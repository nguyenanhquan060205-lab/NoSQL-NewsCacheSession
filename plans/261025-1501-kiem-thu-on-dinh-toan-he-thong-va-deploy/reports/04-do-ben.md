# Phase 4 — Độ bền và lỗi biên (26/10/2026)

Chỉ thao tác trên `news-redis-qa` / `news-mongo-qa` và API QA `:5135` (build từ `develop` @ `9665335`,
cấu hình Redis mặc định: `syncTimeout` 5 s). Container demo `news-redis` / `news-mongo` không bị đụng.

## Số đo bình thường

| Chỉ số | Giá trị |
|---|---|
| `GET /api/posts/{id}` MISS (trung vị 2 × 20 bài seed) | 2,72 ms / 2,69 ms |
| `GET /api/posts/{id}` HIT | 0,77 ms / 0,76 ms |
| RSS API lúc nghỉ | 77,0 MB |
| Kết nối Redis | 2 (`connected_clients`) |

## Kết quả từng kịch bản

### 1. Redis chết khi đang phục vụ — **G9 đúng, nặng hơn dự đoán**

`docker stop news-redis-qa`, gọi từng loại request (cookie là phiên admin hợp lệ):

| Request | Trước khi dừng | Redis đã dừng |
|---|---|---|
| `GET /health` | 200 · 15 ms | 503 · **5 335 ms** |
| `GET /api/posts` | 200 · 3 ms | **500 · 5 989 ms** |
| `GET /api/posts/{id}` (đã cache) | 200 · 1 ms HIT | **500 · 5 995 ms** |
| `GET /api/posts/{id}` (chưa cache) | 200 · 2 ms MISS | **500 · 5 999 ms** |
| `GET /api/posts` có cookie | 200 · 2 ms | **500 · 6 000 ms** |
| `POST /api/posts` có cookie | 201 · 15 ms | **500 · 5 997 ms** |
| `POST /api/auth/login` | 200 · 101 ms | **500 · 5 999 ms** |

Log (gom theo loại):
```
8 × StackExchange.Redis.RedisConnectionException: The message timed out in the backlog attempting
    to send because no connection became available (5000ms) - Last Connection Exception: SocketClosed
6 × fail: Microsoft.AspNetCore.Diagnostics.DeveloperExceptionPageMiddleware[1]
```
Kết luận: không chỉ "trả 500" — thư viện **xếp lệnh vào backlog chờ 5 s** rồi mới ném lỗi, nên mỗi
request treo ~6 s. Bản sửa chỉ bắt exception vẫn để trang chủ treo 5 s × số lệnh Redis (GetAll gọi
3 lệnh → ~15 s). → Thiết kế S1 phải **kiểm tra `IsConnected` trước để báo lỗi tức thì**.

Integration test tái hiện được (trỏ factory vào cổng chết `localhost:6399`, không cần dừng container):
`ResilienceTests.RedisDown_PublicReadsServeFromMongo_SessionActionsReturn503_HealthUnhealthy`
→ `Expected list.StatusCode to be ... OK {value: 200} ..., but found ... InternalServerError {value: 500}.`

### 2. Redis sống lại

`docker start news-redis-qa` → API tự kết nối lại, request đầu tiên trả 200 sau **1,1 s** kể từ lệnh
start (`AbortOnConnectFail=false` hoạt động). `/health` → Healthy. Phiên cũ mất (Redis QA không lưu đĩa).

### 3. Redis mất dữ liệu — **G13 đã sửa, chạy đúng trên stack thật**

```
Mongo views ban đầu: 0
5 lượt xem → {"views":5}
worker flush (≤ 65 s) → Mongo views: 5
docker restart news-redis-qa → DBSIZE=0
lượt xem kế tiếp → {"views":6}            ← khởi tạo từ posts.views, không đếm lại từ 0
worker flush → Mongo views: 6             ← không tụt
```
Giới hạn còn lại (đặc trưng Write-Behind, ghi vào phản biện): lượt xem phát sinh sau lần flush cuối
và trước khi Redis mất dữ liệu (tối đa ~1 phút) sẽ mất.

### 4. MongoDB chết

`docker stop news-mongo-qa`:

| Request | Kết quả |
|---|---|
| `GET /health` | 503 · 30 061 ms |
| `GET /api/posts` (đã cache) | **200 · 4 ms HIT** |
| `GET /api/posts/{id}` (đã cache) | **200 · 3 ms HIT** |
| `GET /api/posts/{id}` (chưa cache) | 500 · 30 018 ms |
| `GET /api/posts` có cookie | 200 · 5 ms HIT |
| `POST /api/posts` có cookie | 500 · 30 013 ms |
| `POST /api/auth/login` | 500 · 30 013 ms |

Redis làm vùng đệm đúng như thiết kế: nội dung đã cache vẫn phục vụ được trong ≤ TTL. Phần còn lại
treo **30 s** (`serverSelectionTimeoutMS` mặc định của driver) rồi 500. Không nằm trong danh sách sửa;
ghi chú cho Phase 6: chuỗi kết nối Atlas nên có `serverSelectionTimeoutMS=5000`. `docker start` → bài
chưa cache đọc lại được ngay.

### 5. API khởi động lại

Dừng PID 27398, chạy lại (PID mới 29323): cookie phiên cũ gọi `/api/auth/me` → **200** (phiên nằm ở
Redis, API không giữ trạng thái); `/api/cache/stats` từ `hits=53, misses=58` → **0/0** (bộ đếm trong RAM).

### 6. Lock kẹt — **G10 đúng**

`SET lock:post:{id} tien-trinh-da-chet PX 5000` rồi `GET /api/posts/{id}`:
```
GET khi lock kẹt: 200 sau 5.044367s
MONITOR: 96 lần "SET lock:post:{id} <token> EX 5 NX", 98 lần "GET post:{id}"
```
→ 96 tầng đệ quy, chờ tới khi lock tự hết hạn. Integration test:
`ResilienceTests.GetById_WhileAnotherHolderKeepsLock_ShouldFallBackToMongoWithinBoundedWait`
→ `Expected watch.Elapsed to be less than 3s and 500ms ..., but found 5s, 61ms`.

Ghi chú G28: MONITOR cho thấy code ghi `SET lock:post:{id} <token 32 hex> EX 5 NX` (giải phóng bằng Lua
so token), còn `docs/redis-keyspace.md` ghi `SET lock:post:{id} 1 NX PX 5000` và `DEL` — doc lệch code.

### 7. Cloudinary chậm — **G14 đúng**

`ResilienceTests.Update_WhileCloudinaryIsSlow_ShouldInvalidateCacheBeforeDeletingOldImage` (kho ảnh giả
chờ 3 s khi xóa ảnh cũ) → `Expected cacheAliveDuringCloudinaryCall to be False ..., but found True.`
MongoDB đã ghi tiêu đề mới nhưng `post:{id}` (bản cũ) còn sống suốt thời gian chờ Cloudinary.

### 8. Worker flush gặp MongoDB lỗi — **G11 đúng**

`ResilienceTests.Flush_WhenMongoWriteFails_ShouldKeepPostIdDirtyForNextRound` (factory trỏ Mongo vào
cổng chết, Redis thật có `posts:dirty_views = {id}`, `post:{id}:views = 42`)
→ `Expected ... SetContainsAsync("posts:dirty_views", postId) to be True ..., but found False.`
ID đã bị SPOP, ghi Mongo lỗi → mất dấu.

### 9. Tải dài 15 phút

Hai luồng `ab -k -t 900 -c 10` chạy song song (chi tiết bài + trang 1 danh sách), lấy mẫu mỗi 30 s:

| | `GET /api/posts/{id}` | `GET /api/posts?page=1&pageSize=10` |
|---|---|---|
| Request hoàn tất | 4 813 219 | 4 654 666 |
| Failed / non-2xx | **0 / 0** | **0 / 0** |
| Thông lượng | 5 348 req/s | 5 172 req/s |
| Độ trễ p50 / p95 / p99 / max | 2 / 3 / 6 / 217 ms | 2 / 3 / 6 / 217 ms |

RSS API (MB) theo từng mốc 30 s: `70, 181, 174, 179, 171, 172, 195, 166, 167, 163, 163, 165, 173, 164,
164, 163, 173, 162, 176, 161, 165, 162, 164, 161, 171, 162, 161, 162, 159, 157, 162` → tăng lúc khởi động
tải rồi **đi ngang ~160–175 MB, không tăng đều**; nghỉ sau tải còn 98 MB (GC trả bớt). Redis
`connected_clients` = 2 suốt 15 phút (multiplexer dùng chung, không rò kết nối), `used_memory` 1,8–4,3 MB.

### 10. Dung lượng cache bài dài — G25

5 bài dài nhất của `newsdb` (chép sang `newsdb_qa`, chỉ đọc từ demo), nạp qua API thật:

| Bài | `content` (ký tự) | `STRLEN post:{id}` | `MEMORY USAGE` |
|---|---|---|---|
| `…3b66` | 275 018 | 569 355 B | 655 432 B |
| `…412e` | 242 991 | 497 436 B | 524 360 B |
| `…3ca6` | 198 190 | 413 914 B | 458 824 B |
| `…4eb7` | 191 602 | 400 277 B | 458 824 B |
| `…3b30` | 190 242 | 389 743 B | 393 288 B |
| bài seed ngắn | — | — | 1 352 B |

JSON cache escape mọi chữ có dấu thành `\uXXXX` (6 byte/ký tự), ví dụ
`"Title":"Chiến tranh Đông Dương"`. Cùng bài đó ghi UTF-8 không escape:
**569 355 → 364 723 byte (−36 %)** → bằng chứng cho S5.

Ước tính Redis Cloud free 30 MB: `newsdb` có 10 150 bài, `content` trung bình 11 374 ký tự (trung vị
~5 094) → mỗi key `post:{id}` trung bình ~23 KB hiện tại, ~15 KB sau S5. Trong 10 phút TTL, 30 MB chứa
được khoảng 1 300 bài khác nhau (hiện tại) / ~2 000 bài (sau S5) — đủ cho bản deploy demo; vẫn cần
eviction `volatile-lru` để key không TTL (`post:{id}:views`, `posts:ver`, `posts:dirty_views`) không bị đẩy ra.

## Kết luận

| # | Kết luận | Sửa ở Phase 5 |
|---|---|---|
| G9 | **Đúng** — mọi request (kể cả bài đã cache) 500 sau ~6 s | S1 (kèm kiểm tra `IsConnected` để không treo 5 s) |
| G10 | **Đúng** — 96 vòng đệ quy, 5,04 s | S2 |
| G11 | **Đúng** — ID mất khỏi `posts:dirty_views` | S3 |
| G13 | **Đã sửa** (`9665335`), xác nhận trên stack thật | — |
| G14 | **Đúng** — cache cũ sống trong lúc chờ Cloudinary | N2 (SV1) + D3 timeout (SV3) |
| G25 | **Đúng** — bài dài nhất 640 KB/key; JSON escape làm phình 36 % | S5 + `volatile-lru` ở Phase 6 |
| G28 | **Đúng** — doc thiếu `posts:dirty_views`, ghi sai lệnh lock | N6 (SV1) |
| Mới | MongoDB sập: request chưa cache treo 30 s | Không sửa code; thêm `serverSelectionTimeoutMS` vào chuỗi kết nối deploy |
