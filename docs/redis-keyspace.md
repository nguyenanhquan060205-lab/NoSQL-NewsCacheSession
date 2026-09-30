# Thiết kế keyspace Redis

Mọi key liên quan bài viết nằm chung namespace `post:` / `posts:` để có thể
`SCAN post:*` gom được cả nội dung cache lẫn bộ đếm lượt xem của một bài.

| Key pattern | Kiểu dữ liệu | TTL | Mô tả |
|---|---|---|---|
| `session:{sessionId}` | Hash | 30 phút (sliding — refresh mỗi request) | Session người dùng: `userId`, `username`, `role`, `loginAt`, `lastActive` |
| `post:{postId}` | String (JSON serialize) | 10 phút | Cache toàn bộ nội dung bài viết cho luồng Cache-Aside |
| `post:{postId}:views` | String (số nguyên) | Không TTL | Bộ đếm lượt xem thời gian thực bằng `INCR` |
| `posts:cat:{categoryId}:p{n}` | String (JSON serialize list) | 3 phút | Cache danh sách bài viết theo chuyên mục, theo trang |
| `lock:post:{postId}` | String | 5 giây | Khóa chống cache stampede — `SET key value NX PX 5000` |

Hằng số tương ứng trong code nằm ở đầu `Controllers/PostsController.cs`
(`CachePrefix`, `ListCachePrefix`, `CacheKey()`, `ViewsKey()`) và
`Services/RedisSessionService.cs`. Sửa key thì sửa cả hai nơi lẫn bảng này.

## Vì sao chọn cấu trúc dữ liệu như vậy

- **Session → Hash**: mỗi phiên có nhiều thuộc tính (`userId`, `username`, `role`,
  `loginAt`, `lastActive`). Dùng Hash cho phép `HGET` đúng một field khi middleware
  chỉ cần `userId`, và `HSET` cập nhật `lastActive` mà không phải đọc–ghi lại toàn
  bộ phiên như khi lưu JSON trong String. `EXPIRE` đặt được trên cả Hash nên TTL
  vẫn hoạt động bình thường.
- **Cache bài viết → String (JSON)**: bài viết luôn được đọc/ghi/xóa nguyên khối
  (không bao giờ chỉ lấy riêng `title`), nên serialize thành một String là đơn giản
  và nhanh nhất; `SET key value EX ttl` làm được cả ghi lẫn đặt TTL trong một lệnh.
- **Bộ đếm lượt xem → String riêng**: `INCR` chỉ chạy trên String. Tách khỏi
  `post:{postId}` để tăng lượt xem không phải deserialize rồi ghi lại cả bài viết,
  và để bộ đếm không bị mất khi cache nội dung hết hạn.

## Vì sao chọn TTL như vậy

- **Session (30 phút, sliding)**: cân bằng giữa trải nghiệm (không bị đăng xuất giữa
  lúc đang soạn bài) và bảo mật (tự hết hạn nếu bỏ máy). Sliding = mỗi request hợp lệ
  lại `EXPIRE` về 30 phút.
- **Cache bài viết (10 phút)**: ngắn hơn session vì nội dung có thể được sửa. Kể cả
  khi Cache Invalidation lỗi (Redis mất kết nối lúc admin sửa bài), dữ liệu cũ cũng
  chỉ tồn tại tối đa 10 phút — TTL là lưới an toàn cho invalidation.
- **Bộ đếm lượt xem (không TTL)**: là số liệu thống kê tích lũy, mất là mất luôn.
  Định kỳ flush ngược về `posts.views` trong MongoDB.
- **Danh sách theo chuyên mục (3 phút)**: ngắn nhất vì danh sách thay đổi thường
  xuyên nhất (bài mới đăng, bài bị xóa) và ảnh hưởng trực tiếp tới trang chủ.
- **Lock (5 giây)**: chỉ cần đủ cho một request truy vấn MongoDB xong (~200ms), đặt
  5 giây để dư an toàn. PX bắt buộc phải có: nếu tiến trình giữ khóa chết giữa đường
  mà khóa không tự hết hạn thì mọi request sau đều bị chặn vĩnh viễn.

## Luồng Cache-Aside (đọc bài viết)

Hiện thực ở `GET /api/posts/{id}`.

1. Nhận request → `GET post:{postId}`.
2. **HIT** → deserialize JSON, trả về ngay (~<5ms).
3. **MISS** → thử giành khóa `SET lock:post:{postId} 1 NX PX 5000`:
   - **Giành được** → query MongoDB → `SET post:{postId} {json} EX 600` → trả về →
     `DEL lock:post:{postId}`.
   - **Không giành được** (request khác đang xử lý) → đợi ngắn rồi đọc lại cache,
     tránh nhiều request cùng đập vào MongoDB (chống cache stampede).

## Cache Invalidation

Khi sửa hoặc xóa bài viết, sau khi MongoDB đã đổi thì xóa ngay key Redis liên quan;
lần đọc tiếp theo sẽ MISS và nạp lại dữ liệu mới.

| Hành động | Key phải xóa |
|---|---|
| Tạo bài viết | `posts:cat:*` (bài mới phải xuất hiện trên trang chủ ngay) |
| Sửa bài viết | `post:{postId}` và `posts:cat:*` |
| Xóa mềm bài viết | `post:{postId}` và `posts:cat:*` |

**Không xóa `post:{postId}:views`** khi xóa mềm: bài viết vẫn có thể phục hồi, và
lượt xem là số liệu tích lũy — phải để job flush chốt về MongoDB trước.

Thứ tự bắt buộc: **ghi MongoDB trước, xóa Redis sau**. Nếu xóa cache trước rồi mới
ghi DB, một request đọc chen vào giữa sẽ nạp lại đúng dữ liệu cũ vào cache và giữ
nó thêm trọn một vòng TTL.
