# Thiết kế keyspace Redis

| Key pattern | Kiểu dữ liệu | TTL | Mô tả |
|---|---|---|---|
| `session:{session_id}` | Hash | 30 phút (sliding — refresh mỗi request) | Lưu session: `user_id`, `username`, `role`, `login_at`, `last_active` |
| `article:{article_id}` | String (JSON serialize) | 5-10 phút | Cache toàn bộ nội dung bài viết cho luồng Cache-Aside |
| `article:{article_id}:views` | String (số nguyên) | Không TTL | Đếm lượt xem bằng lệnh `INCR` |
| `articles:cat:{category_id}:p{n}` | String (JSON serialize list) | 2-3 phút | Cache danh sách bài viết theo chuyên mục, theo trang |
| `lock:article:{article_id}` | String | 5 giây | Khoá chống cache stampede — dùng `SET key value NX PX 5000` |

## Vì sao chọn TTL như vậy
- **Session (30 phút, sliding)**: cân bằng giữa trải nghiệm người dùng (không bị đăng xuất giữa chừng khi đang thao tác) và bảo mật (tự hết hạn nếu không hoạt động).
- **Article cache (5-10 phút)**: ngắn hơn session vì nội dung bài viết có thể được admin chỉnh sửa, cần refresh tương đối thường xuyên để tránh hiển thị dữ liệu cũ quá lâu.
- **View counter (không TTL)**: đây là số liệu thống kê tích luỹ, không nên mất khi cache hết hạn — định kỳ đồng bộ ngược lại MongoDB.
- **List theo category (2-3 phút)**: ngắn nhất vì danh sách dễ thay đổi nhất (bài mới đăng, bài bị xoá).
- **Lock (5 giây)**: chỉ cần đủ thời gian cho 1 request truy vấn MongoDB xong, tránh giữ khoá quá lâu làm nghẽn các request khác.

## Luồng Cache-Aside (đọc bài viết)
1. Nhận request đọc bài viết → kiểm tra `article:{article_id}` trong Redis.
2. Nếu **HIT** → trả về ngay từ Redis.
3. Nếu **MISS** → thử lấy khoá `lock:article:{article_id}` (SET NX PX):
   - Lấy được khoá → query MongoDB, ghi kết quả vào `article:{article_id}` kèm TTL, trả về, xoá khoá.
   - Không lấy được khoá (request khác đang xử lý) → đợi ngắn rồi thử đọc lại cache, tránh gọi MongoDB trùng lặp (chống cache stampede).

## Cache Invalidation
Khi admin sửa/xoá bài viết → xoá ngay key `article:{article_id}` tương ứng trong Redis (invalidate), lần đọc tiếp theo sẽ tự động MISS và load lại dữ liệu mới từ MongoDB.
