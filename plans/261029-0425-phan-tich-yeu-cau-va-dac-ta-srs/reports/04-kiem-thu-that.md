# Báo cáo kiểm thử trên hệ thống chạy thật (Phase 4)

**Dự án:** NoSQL-NewsCacheSession (Đề tài 06)  
**Người thực hiện:** SV2 — Nguyễn Anh Quân  
**Thời gian thực hiện:** 29/10/2026 16:43 – 16:48 (GMT+7)  
**Mục tiêu:** Kiểm chứng trên stack thật những điều checker không đo được: header, cookie, lệnh Redis thật qua MONITOR, worker Write-Behind, số lượng dữ liệu CSDL và các endpoint trên bản deploy đám mây.

---

## 1. Kết quả bộ kiểm thử nền tảng (L1 – L5)

| # | Kiểm tra | Lệnh | Kết quả | Ghi chú |
|---|---|---|---|---|
| L1 | Biên dịch API | `dotnet build src/NewsCacheSession.Api/NewsCacheSession.Api.csproj` | **Build succeeded** (0 Error, 0 Warning) | .NET 8 (net8.0) |
| L2 | Unit tests .NET | `dotnet test` | **Passed: 32, Skipped: 46, Failed: 0** | 46 integration test bỏ qua do chưa bật `NEWS_IT=1` |
| L3 | Toàn bộ kiểm thử .NET | `NEWS_IT=1 dotnet test` (với QA containers) | **Passed: 78, Skipped: 0, Failed: 0** (Thời gian: 18 s) | Toàn bộ 78 unit và integration tests đều xanh 100% |
| L4 | Frontend Vitest | `cd src/frontend && npm test` | **Passed: 11/11 files, 103/103 tests** | React 19, Vitest 4.1 |
| L5 | Python tests | `python3 -m unittest discover` | • DocCheck: **Passed 26/26 tests**<br/>• Benchmark: `test_plot.py` bỏ qua vì môi trường CLI thiếu `matplotlib`<br/>• SeedPosts: bỏ qua vì CLI thiếu `pymongo`<br/>• SeedRedis: 31 passed, 4 skipped, 2 verifier tests | Không sửa mã của SV3; báo cho SV3 |

---

## 2. Kiểm thử sống trên API QA (`http://localhost:5135`, CSDL `newsdb_srs_check`, Redis QA `localhost:6380`)

### L6: Đăng ký bootstrap admin và Đăng nhập nhận cookie
*   **Đăng ký admin đầu tiên**:
    ```bash
    curl -si -X POST http://localhost:5135/api/auth/register \
      -H "Content-Type: application/json" \
      -d '{"username":"admin_qa_test","password":"Password123"}'
    ```
    *Phản hồi*: `HTTP/1.1 201 Created`  
    `{"id":"6ae31593...","username":"admin_qa_test","role":"admin"}`  
    $\rightarrow$ **Chứng minh**: Tài khoản đầu tiên tự động nhận vai trò `admin` theo cơ chế bootstrap nguyên tử (FR-01).

*   **Đăng nhập**:
    ```bash
    curl -si -X POST http://localhost:5135/api/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username":"admin_qa_test","password":"Password123"}'
    ```
    *Phản hồi*: `HTTP/1.1 200 OK`  
    `Set-Cookie: SessionId=309a1f85-e2b9-44fb-bc1c-32b4b30d44ef; max-age=1800; path=/; samesite=lax; httponly`  
    `{"sessionId":"309a1f85-e2b9-44fb-bc1c-32b4b30d44ef","userId":"6ae31593...","username":"admin_qa_test","role":"admin"}`  
    $\rightarrow$ **Chứng minh**: Cookie có tên `SessionId`, `max-age=1800` (30 phút), gắn cờ `httponly` và `samesite=lax` (FR-02, NFR-06).

### L7: Cấu trúc Hash trong Redis và Sliding Expiration
*   **Kiểm tra Redis Hash**:
    ```bash
    docker exec news-redis-qa redis-cli HGETALL session:309a1f85-e2b9-44fb-bc1c-32b4b30d44ef
    ```
    *Kết quả*: Đủ 5 trường: `userId`, `username`, `role` (`admin`), `loginAt` (`1793267095`), `lastActive` (`1793267095`).  
    TTL ban đầu: `1794` giây.
*   **Gọi `GET /api/auth/me` kèm cookie**:
    ```bash
    curl -si -H "Cookie: SessionId=309a1f85-e2b9-44fb-bc1c-32b4b30d44ef" http://localhost:5135/api/auth/me
    ```
    *Phản hồi*: `HTTP/1.1 200 OK`  
    `Set-Cookie: SessionId=309a1f85-e2b9-44fb-bc1c-32b4b30d44ef; max-age=1800; path=/; samesite=lax; httponly`  
    `{"userId":"...","username":"admin_qa_test","role":"admin","expiresInSeconds":1799}`  
    $\rightarrow$ **Chứng minh**: TTL tự động trượt gia hạn về 1799 giây, cookie được cấp lại với Max-Age mới (FR-03, FR-22).

### L8: Luồng Cache-Aside (GET theo ID vs Slug)
*   Tạo chuyên mục (`6ae315b4d354524a8a4097bc`) và bài viết (`6ae315b9d354524a8a4097bd`, slug `bai-viet-thu-nghiem-cache-qa`).
*   Gọi `GET /api/posts/6ae315b9d354524a8a4097bd` lần 1 $\rightarrow$ Header: `X-Cache: MISS`.
*   Gọi `GET /api/posts/6ae315b9d354524a8a4097bd` lần 2 $\rightarrow$ Header: `X-Cache: HIT`.
*   Kiểm tra TTL khóa cache: `docker exec news-redis-qa redis-cli TTL post:6ae315b9d354524a8a4097bd` $\rightarrow$ `594` giây (≤ 600 s / 10 phút).
*   Gọi `GET /api/posts/slug/bai-viet-thu-nghiem-cache-qa` $\rightarrow$ Không tạo ra bất kỳ khóa `post:*` mới nào trên Redis.  
    $\rightarrow$ **Chứng minh**: Luồng Cache-Aside hoạt động chính xác tại `{id}` và endpoint slug cố ý không cache (FR-10, FR-12).

### L9: Cache Invalidation khi cập nhật bài viết
*   Trước cập nhật: `posts:ver` = `1`.
*   Gọi `PUT /api/posts/6ae315b9d354524a8a4097bd` với tiêu đề `"Tiêu Đề Bài Viết Đã Cập Nhật QA"`.
*   Kiểm tra Redis:
    *   `docker exec news-redis-qa redis-cli EXISTS post:6ae315b9d354524a8a4097bd` $\rightarrow$ **`0`** (đã bị xóa).
    *   `docker exec news-redis-qa redis-cli GET posts:ver` $\rightarrow$ **`2`** (đã tăng 1).
*   Gọi `GET /api/posts/6ae315b9d354524a8a4097bd` ngay sau đó $\rightarrow$ Header `X-Cache: MISS`, nội dung trả về tiêu đề mới.  
    $\rightarrow$ **Chứng minh**: Cache Invalidation tức thời và cơ chế số phiên bản danh sách hoạt động chính xác (FR-07, FR-14, FR-16).

### L10: Chụp log MONITOR xác thực lệnh Khóa phân tán (Distributed Lock)
Chạy lệnh `docker exec news-redis-qa redis-cli MONITOR` trong quá trình xảy ra Cache MISS:
```text
"DEL" "post:6ae315b9d354524a8a4097bd"
"GET" "post:6ae315b9d354524a8a4097bd"
"SET" "lock:post:6ae315b9d354524a8a4097bd" "e2aca6fed71b448b8f30520fb871fb3d" "EX" "5" "NX"
"GET" "post:6ae315b9d354524a8a4097bd"
"GET" "post:6ae315b9d354524a8a4097bd:views"
"SETEX" "post:6ae315b9d354524a8a4097bd" "600" "{json}"
"WATCH" "lock:post:6ae315b9d354524a8a4097bd"
"GET" "lock:post:6ae315b9d354524a8a4097bd"
"UNLINK" "lock:post:6ae315b9d354524a8a4097bd"
```
$\rightarrow$ **Chứng minh bằng chứng thực nghiệm**:
1. Lệnh cấp khóa: `"SET" "lock:post:{id}" "<token>" "EX" "5" "NX"` (đơn vị TTL là giây `EX 5`).
2. Lệnh lưu cache: `"SETEX" "post:{id}" "600" "{json}"`.
3. Giao dịch giải phóng khóa so token an toàn: `"WATCH"` $\rightarrow$ `"GET"` $\rightarrow$ `"UNLINK"`. Hoàn toàn khớp với mô tả trong SRS v3.0 (FR-13, D14, S5).

### L11: Bộ đếm INCR và Tiến trình Write-Behind Flush
*   Gọi `POST /api/posts/6ae315b9d354524a8a4097bd/view` 3 lần liên tiếp:
    *   Phản hồi lần lượt: `{"views":1}`, `{"views":2}`, `{"views":3}`.
*   Kiểm tra Redis:
    *   `GET post:6ae315b9d354524a8a4097bd:views` = `3`.
    *   `SMEMBERS posts:dirty_views` chứa `"6ae315b9d354524a8a4097bd"`.
*   Kiểm tra MongoDB trước khi flush: `db.posts.findOne({_id: ...})` $\rightarrow$ `views: 0`.
*   Chờ 65 giây (vượt qua chu kỳ 60 s của `ViewCountSyncWorker`):
    *   MongoDB: `views` được cập nhật thành **`3`**.
    *   Redis: `posts:dirty_views` được làm rỗng.  
    $\rightarrow$ **Chứng minh**: Cơ chế Write-Behind hoạt động hoàn hảo (FR-17, FR-18).

### L12: Endpoint Thống kê Cache
*   Gọi `GET http://localhost:5135/api/cache/stats`:
    ```json
    {"hits":1,"misses":3,"totalRequests":4,"hitRate":25}
    ```
    $\rightarrow$ **Chứng minh**: Trả đúng 4 trường `hits, misses, totalRequests, hitRate` (FR-19, D4).

---

## 3. Kiểm thử trên Stack Demo cục bộ (Chỉ đọc)

*   **L13 (RedisInsight)**: `curl -s -o /dev/null -w '%{http_code}' localhost:5540` $\rightarrow$ **`200 OK`**. Cổng 5540 hoạt động bình thường (D6).
*   **L14 (Dữ liệu MongoDB `newsdb`)**:
    *   Tổng số bài viết: **10.251** bài.
    *   Số bài viết hoạt động (`isDeleted != true`): **10.150** bài.
    *   Số chuyên mục: **7** chuyên mục.
    *   Số bài có `imageUrl` hợp lệ: **10.251** bài (100%).
*   **L15 (Redis demo keys)**:
    *   Lệnh scan `session:*` và `post:*` thực thi nhanh, không phát sinh lỗi.

---

## 4. Kiểm thử trên Bản Triển khai Đám mây (Deploy Stack — Chỉ GET)

*API: `https://newscachesession-api.onrender.com` \| Web: `https://no-sql-news-cache-session.vercel.app`*

| # | Kiểm tra | Lệnh gọi | Kết quả đo được |
|---|---|---|---|
| L16 | Endpoint sức khỏe `/health` | `curl -s --max-time 120 <API>/health` | Status: **Healthy**<br/>• mongodb: Healthy (2.1 ms)<br/>• redis: Healthy (Latency: 1.96 ms) |
| L17 | Lấy bài viết đầu tiên & Tổng số bài | `curl -si "<API>/api/posts?page=1&pageSize=1"` | Header `x-cache: MISS`, `totalItems: 10000`, 7 chuyên mục, bài đầu ID `6ac6af8f5cdee79754d43ab8` |
| L18 | Kiểm tra Cache-Aside trên Render | `curl -si "<API>/api/posts/6ac6af8f5cdee79754d43ab8"` ×2 | Lần 1: `x-cache: MISS`<br/>Lần 2: `x-cache: HIT` |
| L19 | Thống kê Cache trên đám mây | `curl -s "<API>/api/cache/stats"` | `{"hits":1,"misses":2,"totalRequests":3,"hitRate":33.33}` |
| L20 | Giao diện Vercel & Chuyên mục | `curl -s -o /dev/null -w '%{http_code}' <WEB>` | **200 OK**, danh mục trả về đúng 7 chuyên mục |

---

## 5. Dọn dẹp tài nguyên QA

- Tiến trình API QA (PID / Task ID) đã được dừng hoàn toàn.
- Hai container QA `news-mongo-qa` và `news-redis-qa` đã được gỡ bỏ bằng `docker rm -f`.
- Hệ thống trở về nguyên trạng với 3 container demo ban đầu (`news-mongo`, `news-redis`, `news-redisinsight`).

