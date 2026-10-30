# Thiết kế keyspace Redis

Mọi key liên quan bài viết nằm chung namespace `post:` / `posts:` để có thể
`SCAN post:*` gom được cả nội dung cache lẫn bộ đếm lượt xem của một bài.

| Key pattern | Kiểu dữ liệu | TTL | Mô tả |
|---|---|---|---|
| `session:{sessionId}` | Hash | 30 phút (sliding — refresh mỗi request) | Session người dùng: `userId`, `username`, `role`, `loginAt`, `lastActive` |
| `post:{postId}` | String (JSON serialize) | 10 phút | Cache toàn bộ nội dung bài viết cho luồng Cache-Aside |
| `post:{postId}:views` | String (số nguyên) | Không TTL | Bộ đếm lượt xem thời gian thực bằng `INCR` |
| `posts:cat:{categoryId}:p{n}:v{ver}` | String (JSON serialize list) | 3 phút | Cache danh sách bài viết theo chuyên mục, theo trang |
| `posts:ver` | String (số nguyên) | Không TTL | Số phiên bản cache danh sách — `INCR` để vô hiệu hóa toàn bộ |
| `lock:post:{postId}` | String | 5 giây | Khóa chống cache stampede — `SET key <token ngẫu nhiên> NX EX 5`, giải phóng bằng transaction so token |
| `posts:dirty_views` | Set | Không TTL | ID các bài có lượt xem chưa chốt về MongoDB — `SADD` mỗi lượt xem, worker `SPOP` mỗi phút (Write-Behind) |

Hằng số tương ứng trong code nằm ở đầu `Controllers/PostsController.cs`
(`CachePrefix`, `ListCachePrefix`, `ListVersionKey`, `CacheKey()`, `ViewsKey()`),
`Services/RedisSessionService.cs`, `Services/CurrentUserService.cs` và
`Services/RedisCacheService.cs` (`posts:dirty_views`).
Sửa key thì sửa cả code lẫn bảng này.

### Field trong Hash `session:{sessionId}`

| Field | Ai ghi | Ghi chú |
|---|---|---|
| `userId`, `username`, `role`, `loginAt`, `lastActive` | `AuthController.Login` → `RedisSessionService.CreateSessionAsync` | Cả 5 field + `EXPIRE` trong **một** `MULTI/EXEC`; thời điểm là Unix seconds |
| `lastActive` (cập nhật) | `SessionAuthMiddleware` → `RedisSessionService.RefreshSessionAsync` | Mỗi request có phiên hợp lệ, cùng transaction với `EXPIRE` (sliding) |
| `role` (bổ sung) | `CurrentUserService.TouchAsync` | Chỉ cho phiên tạo bởi bản code cũ chưa có field này |

`role` được ghi vào Hash ngay lúc đăng nhập để mọi request sau đó biết người gọi có
phải admin hay không **mà không phải query MongoDB**. Phiên tạo bởi bản code cũ chưa
có field này thì được tra bù một lần rồi ghi lại vào Hash.

Tạo phiên phải là một `MULTI/EXEC`: gửi `HSET` rồi `EXPIRE` thành hai lệnh rời thì tiến
trình chết giữa chừng để lại một Hash không TTL nằm vĩnh viễn trong Redis. TTL lấy từ
`SessionSettings:TtlMinutes` (mặc định 30) cho cả Hash lẫn `Max-Age` cookie; middleware cấp
lại cookie mỗi lần gia hạn để cookie trượt cùng TTL trên Redis.

`HSET` trên key đã tồn tại **không xóa TTL**, nên ghi thêm field không làm phiên mất
hạn hay được gia hạn ngoài ý muốn — đã kiểm chứng bằng `TTL session:{id}` sau khi ghi.

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
  5 giây để dư an toàn. TTL bắt buộc phải có: nếu tiến trình giữ khóa chết giữa đường
  mà khóa không tự hết hạn thì mọi request sau đều bị chặn vĩnh viễn.
- **Tập `posts:dirty_views` (không TTL)**: là hàng đợi việc của worker — hết hạn thì
  lượt xem đã đếm trên Redis không bao giờ được chốt về MongoDB.

## Luồng Cache-Aside (đọc bài viết)

Hiện thực ở `GET /api/posts/{id}`.

1. Nhận request → `GET post:{postId}`.
2. **HIT** → deserialize JSON, trả về ngay (~<5ms).
3. **MISS** → thử giành khóa `SET lock:post:{postId} <token> NX EX 5` (token ngẫu nhiên
   của request — `LockTake` của StackExchange.Redis):
   - **Giành được** → đọc lại cache một lần nữa → query MongoDB →
     `SET post:{postId} {json} EX 600` → trả về → giải phóng khóa bằng transaction có điều kiện
     (`WATCH` → `GET` so token → `MULTI`/`UNLINK`/`EXEC` — `LockRelease`), chỉ xóa khi giá trị
     đúng token của mình, để không xóa nhầm khóa của request khác khi khóa của mình đã hết hạn.
   - **Không giành được** (request khác đang xử lý) → đợi 50ms rồi đọc lại cache, tối đa
     40 lượt (2 giây), tránh nhiều request cùng đập vào MongoDB (chống cache stampede).
     Hết lượt mà vẫn không có cache (tiến trình giữ khóa đã chết) → đọc thẳng MongoDB và
     **không** ghi cache.

### Khi Redis không sẵn sàng

Cache chỉ là bản sao: đọc cache lỗi thì coi như MISS và đọc thẳng MongoDB; ghi/xóa cache
lỗi thì bỏ qua (bản cũ tự hết theo TTL — đây là lý do cache bài viết chỉ sống 10 phút).
Đăng nhập, kiểm tra phiên, đếm lượt xem bắt buộc cần Redis nên trả **503**. Trước mỗi lệnh,
code kiểm tra kết nối để báo lỗi ngay, không xếp hàng chờ 5 giây trong backlog của thư viện.

## Bộ đếm lượt xem (Write-Behind)

`POST /api/posts/{id}/view` → `INCR post:{postId}:views` + `SADD posts:dirty_views {postId}`.
Lượt xem đầu tiên (key đếm chưa có) khởi tạo bằng `SET NX` từ `posts.views` trong MongoDB,
nên Redis mất dữ liệu cũng không đếm lại từ 0. `ViewCountSyncWorker` mỗi phút `SPOP` hết
`posts:dirty_views` rồi ghi giá trị đếm về `posts.views`; ghi MongoDB lỗi thì trả ID về Set
để lượt sau thử lại.

## Cache Invalidation

Khi sửa hoặc xóa bài viết, sau khi MongoDB đã đổi thì xóa ngay key Redis liên quan;
lần đọc tiếp theo sẽ MISS và nạp lại dữ liệu mới.

| Hành động | Việc phải làm |
|---|---|
| Tạo bài viết | `INCR posts:ver` (bài mới phải lên trang chủ ngay) |
| Sửa bài viết | `DEL post:{postId}` + `INCR posts:ver` |
| Xóa mềm bài viết | `DEL post:{postId}` + `INCR posts:ver` |

### Vì sao cache danh sách dùng số phiên bản thay vì xóa key

Cache một bài viết chỉ có đúng một key nên `DEL` là xong. Nhưng cache danh sách thì
rải ra rất nhiều key: mỗi chuyên mục × mỗi số trang. Muốn xóa hết phải `SCAN` tìm
rồi `DEL` từng cái — chi phí O(N) theo số key và phải lặp nhiều lượt.

Thay vào đó, số phiên bản `posts:ver` được ghép vào key:
`posts:cat:{categoryId}:p{page}:v{ver}`. Mỗi lần dự liệu đổi chỉ cần **một lệnh `INCR`**:
toàn bộ key cũ mang số phiên bản nhỏ hơn nên không ai tra tới nữa, và tự biến mất khi
hết TTL 3 phút. Đây là mẫu *cache key versioning* (hay *generational caching*).

Đánh đổi: trong tối đa 3 phút, Redis còn giữ cả bản cũ lẫn bản mới nên tốn thêm
bộ nhớ. Với danh sách bài viết thì không đáng kể, và đổi lại được invalidation O(1)
không chặn Redis.

`posts:ver` **không đặt TTL**: nếu key này hết hạn rồi quay về 0 thì các key cache cũ
(vẫn còn số phiên bản cao hơn) có thể bị tra lại — đọc ra dự liệu cũ.

**Không xóa `post:{postId}:views`** khi xóa mềm: bài viết vẫn có thể phục hồi, và
lượt xem là số liệu tích lũy — phải để job flush chốt về MongoDB trước.

Thứ tự bắt buộc: **ghi MongoDB trước, xóa Redis sau**. Nếu xóa cache trước rồi mới
ghi DB, một request đọc chen vào giữa sẽ nạp lại đúng dữ liệu cũ vào cache và giữ
nó thêm trọn một vòng TTL.
