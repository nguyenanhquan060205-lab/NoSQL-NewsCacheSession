# Báo cáo tiến độ đồ án — Đề tài 06

**Môn:** Dữ liệu NoSQL · **Đề tài 06:** Phân hệ Caching bài viết và Quản lý phiên
**Nhóm 3 người:** Hồ Ngọc Phương Như (SV1) · Nguyễn Anh Quân (SV2) · Nguyễn Xuân Định (SV3)
**Ngày báo cáo:** 23/10/2026 · **Hạn nộp:** 26/10/2026
**Mã nguồn:** nhánh `main` tại commit `b2adb96`

> **Về tài liệu này.** Mọi điều viết ở đây đều kiểm chứng được bằng mã nguồn, lịch sử
> commit, hoặc lần chạy thử thật ngày 23/10/2026. Việc chưa làm được ghi thẳng là **chưa
> làm**. Mục cuối cùng liệt kê những chỗ chưa xác minh được, để nhóm tự kiểm trước khi
> trình bày.

---

## 1. Dự án này là gì

### 1.1 Giải thích dễ hiểu nhất

Hãy tưởng tượng một **thư viện rất lớn**. Mỗi khi có người hỏi mượn một cuốn sách, thủ
thư phải đi vào kho, tìm đúng kệ, rút sách ra rồi mang tới. Mất thời gian. Mà nếu trăm
người cùng hỏi đúng một cuốn sách nổi tiếng, thủ thư phải chạy vào kho **cả trăm lần** để
lấy cùng một cuốn.

Nhóm em làm cho thủ thư một thứ đơn giản: **một cái bàn nhỏ ngay cửa**. Cuốn sách nào vừa
có người hỏi thì đặt luôn lên bàn đó. Người tiếp theo hỏi cùng cuốn ấy, thủ thư **với tay
lấy trên bàn**, không phải vào kho nữa.

- **Cái kho lớn** chính là **MongoDB** — nơi lưu thật, lưu lâu dài, mất là mất hẳn.
- **Cái bàn nhỏ ngay cửa** chính là **Redis** — nhanh hơn rất nhiều, nhưng chỉ giữ tạm.

Trên bàn đó cũng có **một cuốn sổ ghi ai đang ở trong thư viện**. Ai vừa vào thì ghi tên,
và cái tên đó **tự xóa sau 30 phút không hoạt động** — giống **vé gửi xe có ghi giờ hết
hạn**. Đó chính là **quản lý phiên đăng nhập**.

Còn một chuyện quan trọng nữa: **nếu cuốn sách trên bàn bị sửa nội dung thì sao?** Nhóm em
quy định: sửa thì **sửa trong kho trước**, xong mới **bỏ cuốn cũ trên bàn đi**. Lần sau có
người hỏi, thủ thư buộc phải vào kho lấy bản mới. Nhờ vậy không ai đọc nhầm bản cũ.

> **Câu chốt:** Đồ án làm một trang tin tức chạy nhanh hơn nhờ ghi nhớ tạm kết quả đọc,
> và quản lý người đăng nhập bằng "vé có giờ hết hạn".

### 1.2 Vấn đề cần giải quyết

Mỗi lần người đọc mở một bài viết, hệ thống phải hỏi cơ sở dữ liệu. Một bài nổi tiếng có
hàng nghìn lượt đọc thì cơ sở dữ liệu phải trả lời hàng nghìn lần **cùng một nội dung**.
Vừa chậm, vừa phí.

### 1.3 Kết quả mong đợi

1. Lần đọc đầu tiên lấy từ MongoDB; các lần sau lấy từ Redis, **nhanh hơn**.
2. Khi bài viết bị sửa, bản ghi nhớ cũ **phải biến mất ngay**, không ai đọc phải bản cũ.
3. Phiên đăng nhập **tự hết hạn** sau 30 phút không dùng, và **được gia hạn** mỗi khi
   người dùng còn hoạt động.

---

## 2. Hệ thống làm được gì

### 2.1 Sản phẩm là gì

Sản phẩm là một **trang báo điện tử có phần quản trị**. Tên hiển thị trên thanh tiêu đề là
*NEWSCACHE — Chuyên trang tin tức*: đầu trang có ngày tháng, bên dưới là thanh chuyên mục
nằm ngang, trang chủ có khu "Tin nổi bật" rồi tới danh sách bài chia theo trang. Mở một
bài sẽ sang trang chi tiết có nội dung và số lượt xem.

Dữ liệu bài viết, tài khoản và chuyên mục lưu trong **MongoDB**. **Redis** đảm nhận hai
việc: **ghi nhớ tạm nội dung bài viết** để lần đọc sau nhanh hơn, và **giữ phiên đăng
nhập** có thời hạn tự hết.

Trọng tâm của đề tài là **phần caching và quản lý phiên**, nên trang web được làm vừa đủ
để trình diễn hai thứ đó: đọc bài viết là đường đi có cache, đăng nhập là đường đi có
phiên. Các chức năng ngoài trọng tâm này không nằm trong phạm vi đồ án.

> **Câu chốt:** Một trang tin tức có phần quản trị, chạy trên MongoDB làm kho dữ liệu và
> Redis làm bộ nhớ đệm kiêm quản lý phiên.

### 2.2 Chức năng người dùng nhìn thấy

| Nhóm | Chức năng |
|---|---|
| **Khách** | Xem trang chủ, lọc theo chuyên mục, phân trang, mở bài chi tiết, thấy số lượt xem |
| **Người đăng nhập** | Đăng ký, đăng nhập, đăng xuất, viết bài, sửa/xóa **bài của chính mình** |
| **Quản trị viên** | Sửa/xóa **mọi bài**, tạo chuyên mục, xem danh sách phiên đang đăng nhập, buộc đăng xuất một phiên |
| **Phục vụ demo** | Trang chi tiết hiện **huy hiệu HIT/MISS** và thời gian phản hồi, để thấy ngay bài được lấy từ đâu |

Một điểm thiết kế đáng chú ý: **người đăng ký tài khoản đầu tiên tự động thành quản trị
viên**. Làm vậy để không phải cài sẵn một tài khoản admin có mật khẩu nằm lộ trong file
cấu hình.

---

## 3. Thiết kế

### 3.1 Kiến trúc tổng quan (mô tả bằng chữ)

Có **bốn tầng**, xếp từ ngoài vào:

1. **Trình duyệt** chạy giao diện React. Mọi lời gọi dữ liệu đi tới địa chỉ `/api/...`.
2. **API ASP.NET Core 8**. Trước khi vào xử lý, mỗi yêu cầu đi qua một **lớp chặn**
   (middleware): nó đọc mã phiên trong cookie, tra Redis xem phiên còn sống không, rồi
   **gia hạn thời gian sống của phiên**.
3. **Redis** — một máy chủ duy nhất, giữ ba thứ: bản ghi nhớ bài viết, phiên đăng nhập, và
   các bộ đếm.
4. **MongoDB** — nơi lưu thật bài viết, tài khoản, chuyên mục.

Ngoài ra có **một tiến trình chạy nền** cứ mỗi phút lại lấy số lượt xem tích trong Redis
ghi ngược về MongoDB.

> **Câu chốt:** Trình duyệt → API (có lớp chặn kiểm tra phiên) → Redis trước, MongoDB sau.

### 3.2 Vì sao MongoDB cho dữ liệu, Redis cho cache và phiên

| | MongoDB | Redis |
|---|---|---|
| Vai trò | **Nguồn sự thật** — mất là mất hẳn | **Bản sao tạm** — mất vẫn dựng lại được |
| Lưu ở đâu | Ổ đĩa | Bộ nhớ trong |
| Tốc độ | Chậm hơn | Nhanh hơn |
| Vì sao chọn | Bài viết có cấu trúc linh hoạt, không cần ràng buộc bảng cứng nhắc | Có sẵn **thời gian sống tự động (TTL)**, có lệnh **tăng số nguyên tử (INCR)**, có **cấu trúc Hash** đúng như đề bài yêu cầu |

Quan trọng: **toàn bộ cache có thể mất mà nghiệp vụ vẫn đúng** — chỉ chậm đi. Hai ngoại lệ
là bộ đếm lượt xem và bộ đếm phiên bản danh sách, nên hai thứ đó được đặt **không có thời
hạn**.

> **Câu chốt:** MongoDB giữ sự thật, Redis giữ tốc độ.

### 3.3 Mô hình dữ liệu MongoDB

Ba bộ sưu tập (collection): **`posts`**, **`users`**, **`categories`**.

Quy ước bắt buộc của nhóm: **tên trường viết kiểu camelCase** (`createdAt`,
`passwordHash`, `isDeleted`, `imageUrl`, `categoryId`, `authorId`). Lý do: thư viện kết
nối MongoDB của C# mặc định lấy đúng tên thuộc tính trong code (kiểu `CreatedAt`), trong
khi script nạp dữ liệu viết bằng Python dùng camelCase. Hai bên lệch nhau thì **ghi vẫn
thành công nhưng đọc ra bài viết rỗng tiêu đề và ngày tạo sai** — lỗi rất khó nhận ra.

`categoryId` và `authorId` lưu dạng **ObjectId tham chiếu** sang bộ sưu tập khác, không
nhúng cả đối tượng vào bài viết. Lý do: nếu nhúng, đổi tên một chuyên mục là phải sửa hàng
chục bài.

**Xóa bài là xóa mềm** — chỉ đánh dấu `isDeleted`, dữ liệu vẫn còn, có thể phục hồi.

> **Câu chốt:** Ba bộ sưu tập, tên trường camelCase, tham chiếu thay vì nhúng, xóa mềm.

### 3.4 Bảng các key Redis

| Tên key | Kiểu dữ liệu | Thời gian sống (TTL) | Dùng để làm gì |
|---|---|---|---|
| `session:{sessionId}` | **Hash** | 30 phút, **tự gia hạn** khi còn hoạt động | Lưu phiên đăng nhập: `userId`, `username`, `role`, `loginAt`, `lastActive` |
| `post:{postId}` | String (JSON) | 10 phút | Bản ghi nhớ nội dung một bài viết |
| `post:{postId}:views` | String (số) | **Không hết hạn** | Bộ đếm lượt xem thời gian thực, tăng bằng `INCR` |
| `posts:cat:{categoryId}:p{n}:v{ver}` | String (JSON) | 3 phút | Bản ghi nhớ một trang danh sách bài |
| `posts:ver` | String (số) | **Không hết hạn** | Số phiên bản của cache danh sách |
| `posts:dirty_views` | Set | **Không hết hạn** | Hàng đợi các bài có lượt xem chưa ghi về MongoDB |
| `lock:post:{postId}` | String | **5 giây** | Khóa tạm, chống nhiều yêu cầu cùng lúc đập vào MongoDB |

**Vì sao phiên dùng Hash còn bài viết dùng String:** một phiên gồm nhiều mẩu thông tin
nhỏ, cần đọc riêng một mẩu và sửa riêng một mẩu — Hash làm được việc đó mà không phải đọc
rồi ghi lại cả phiên. Bài viết thì luôn dùng nguyên khối, nên String đơn giản và nhanh
hơn.

**Vì sao bộ đếm lượt xem tách thành key riêng:** lệnh tăng số `INCR` chỉ chạy trên String,
không chạy trên một trường bên trong JSON; và quan trọng hơn, bản ghi nhớ nội dung hết hạn
sau 10 phút nhưng **bộ đếm thì không được mất**.

> **Câu chốt:** Truy cập từng phần thì dùng Hash; truy cập nguyên khối thì dùng String.

### 3.5 Cơ chế Cache-Aside (đọc bên cạnh cache)

Luồng đọc một bài viết tại `GET /api/posts/{id}`:

1. **Hỏi Redis trước.** Có sẵn → trả về ngay, gắn nhãn `X-Cache: HIT`.
2. **Không có** → giành một **khóa tạm** `lock:post:{id}` trong 5 giây.
3. Giành được khóa → **kiểm tra lại cache một lần nữa** (phòng khi vừa có người khác nạp
   xong), rồi đọc MongoDB, ghi kết quả vào Redis kèm hạn 10 phút, gắn nhãn `X-Cache: MISS`.
4. **Không giành được khóa** → chờ 50 mili giây rồi **thử lại từ đầu**, thay vì cùng nhau
   đập vào MongoDB.
5. Dù thành công hay lỗi, khóa **luôn được nhả ra** ở bước cuối.

**Vì sao khóa bắt buộc có hạn 5 giây:** nếu tiến trình đang giữ khóa bị chết giữa chừng mà
khóa không tự hết hạn, **mọi yêu cầu sau đó sẽ bị chặn vĩnh viễn**. Đây là lỗi kinh điển
khi tự viết khóa phân tán.

Một điểm cố ý: endpoint đọc theo đường dẫn thân thiện `GET /api/posts/slug/{slug}`
**không được cache**. Nó được giữ làm **mốc đo "trước khi có cache"** để so sánh hiệu năng.

> **Câu chốt:** Hỏi Redis trước, chỉ một yêu cầu được phép đi hỏi MongoDB, kết quả ghi lại
> cho lần sau.

### 3.6 Vì sao mỗi loại một mức thời gian sống

| Key | TTL | Lý do |
|---|---|---|
| Phiên đăng nhập | 30 phút, tự gia hạn | Đủ dài để không bị đăng xuất giữa lúc đang soạn bài; đủ ngắn để tự hết nếu bỏ máy |
| Bài viết | 10 phút | **TTL là lưới an toàn** — nếu Redis mất kết nối đúng lúc sửa bài, bản cũ cũng chỉ sống tối đa 10 phút |
| Danh sách bài | 3 phút | Danh sách thay đổi thường xuyên nhất |
| Bộ đếm lượt xem | Không hết hạn | Số liệu tích lũy, mất là mất luôn |
| Số phiên bản danh sách | Không hết hạn | Nếu nó hết hạn rồi quay về 0, các key cũ mang số lớn hơn có thể bị tra lại → đọc nhầm dữ liệu cũ |

### 3.7 Xóa cache khi dữ liệu đổi (invalidation)

**Thứ tự bắt buộc: ghi MongoDB trước, xóa Redis sau.** Nếu làm ngược lại, một yêu cầu đọc
chen vào giữa sẽ nạp lại **đúng dữ liệu cũ** vào cache và giữ nó thêm **trọn một vòng
TTL**.

Với **một bài viết**, chỉ có một key nên xóa thẳng là xong.

Với **danh sách bài** thì khác: cache danh sách rải ra rất nhiều key (mỗi chuyên mục nhân
mỗi số trang). Muốn xóa hết phải quét tìm rồi xóa từng cái — tốn thời gian tỉ lệ với số
key.

**Giải pháp đã chọn: gắn số phiên bản vào chính tên key.** Khi dữ liệu đổi, chỉ cần **một
lệnh tăng số** `posts:ver`. Các key cũ mang số nhỏ hơn **không còn ai tra tới** và tự biến
mất khi hết hạn 3 phút.

**Đánh đổi phải nói thẳng:** trong tối đa 3 phút, Redis giữ cả bản cũ lẫn bản mới nên tốn
thêm bộ nhớ. Với quy mô đồ án thì không đáng kể.

> **Câu chốt:** Xóa cả một nhóm cache bằng **một lệnh tăng số**, thay vì quét và xóa từng
> key.

### 3.8 Đếm lượt xem kiểu ghi trễ (write-behind)

Mỗi lượt xem **không** ghi thẳng vào MongoDB. Thay vào đó:

1. Tăng bộ đếm trong Redis bằng `INCR`.
2. Đánh dấu bài đó vào một danh sách "cần đồng bộ".
3. **Một tiến trình nền chạy mỗi phút** lấy danh sách đó ra và ghi gộp về MongoDB.

Nhờ vậy, một trang có nghìn lượt đọc chỉ sinh ra **một lần ghi** vào MongoDB mỗi phút, thay
vì nghìn lần ghi.

**Quy định đi kèm:** khi xóa mềm một bài, **không xóa bộ đếm lượt xem của bài đó** — vì bài
có thể được phục hồi, và phải để tiến trình nền chốt số về MongoDB trước.

> **Câu chốt:** Đếm nhanh trong Redis, ghi gộp về MongoDB mỗi phút.

---

## 4. Tiến độ theo barem 4 phần × 2,5 điểm

Nguồn đối chiếu: `docs/checklist-barem.md`.

| Phần | Điểm | Phụ trách | Trạng thái |
|---|---|---|---|
| 1. Báo cáo & Thiết kế cơ sở dữ liệu | 2,5 | SV2 (1,0) + SV1 (1,5) | **Một phần** |
| 2. Chức năng CRUD nền tảng | 2,5 | SV1 | **Xong** |
| 3. Chức năng nâng cao | 2,5 | SV2 | **Xong** |
| 4. Kiểm thử hiệu năng & Demo | 2,5 | SV3 | **Một phần — phần đo hiệu năng chưa làm** |

### Phần 1 — Báo cáo & Thiết kế CSDL (2,5đ): **một phần**

| | |
|---|---|
| **Đã có** | `docs/bao-cao-nguyen-ly-cache-aside.md` (115 dòng, 5 chương) — phần 1,0đ của SV2, commit `6c988ec` |
| | `docs/redis-keyspace.md`, `docs/mongodb-schema.md`, `docs/chot-thiet-ke-sv1.md` — phần 1,5đ của SV1, commit `2fbaa8e` và `559fdb8` |
| **Còn thiếu** | Chương thiết kế của SV1 **chưa có sơ đồ luồng nào** và **chưa có ảnh chụp RedisInsight làm bằng chứng**; ba file hiện vẫn rời rạc, viết cho lập trình viên đọc chứ chưa phải định dạng chương báo cáo |
| | Chương của SV2 có mục "Kết quả thực nghiệm" nhưng **chưa có số để điền**, vì phụ thuộc phần đo của SV3 |

### Phần 2 — Chức năng CRUD nền tảng (2,5đ): **xong**

| | |
|---|---|
| **Đã có** | Đăng ký / đăng nhập / đăng xuất / xem phiên hiện tại — `AuthController.cs`, commit `9aa060e` |
| | Danh sách bài có phân trang và lọc chuyên mục — commit `fac2e8e`; chi tiết theo đường dẫn thân thiện — commit `37923a7` |
| | Tạo / sửa / xóa mềm bài viết — commit `9977987`, `bcb87e0` |
| | Chuyên mục và tự tạo chỉ mục MongoDB — commit `4eea535` |
| | Phân quyền admin / tác giả — commit `163b0e5`; quản lý phiên cho admin — commit `f9d0987` |
| **Còn thiếu** | **Không có test tự động nào phủ phần CRUD này.** Kiểm chứng duy nhất là chạy tay qua HTTP, và **nhật ký lần chạy đó không nằm trong repo** |

### Phần 3 — Chức năng nâng cao (2,5đ): **xong**

| | |
|---|---|
| **Đã có** | Phiên lưu bằng Hash + lớp chặn gia hạn — commit `c8431bf` |
| | Cache-Aside kèm khóa chống dồn — commit `fecb48e` |
| | Đếm lượt xem bằng `INCR` + tiến trình nền ghi về MongoDB — commit `f9babea` |
| | Cache danh sách theo số phiên bản — commit `ef43a20` |
| | 6 file test tự động (xUnit) — commit `ab0e5d4` |
| **Rủi ro** | Dự án test nhắm **.NET 10** còn API nhắm **.NET 8**. Máy chỉ có SDK 9 thì `dotnet test` **hỏng ngay lúc biên dịch** (mã lỗi `NETSDK1045`). Đây là lệch cấu hình, **không phải lỗi mã nguồn** |

### Phần 4 — Kiểm thử hiệu năng & Demo (2,5đ): **một phần**

| | |
|---|---|
| **Đã có (phần dữ liệu mẫu ~1,0đ)** | `scripts/SeedPosts/seed.py` nạp tối thiểu 100 bài có ảnh (chặn cứng nếu yêu cầu dưới 100) — commit `21a1cd4` |
| | `scripts/SeedRedis/seed_redis.py` nạp 20–50 session/cache key có thời hạn khác nhau — commit `6088fe2` |
| | Giao diện đầy đủ: trang chủ, chi tiết, đăng nhập, soạn bài, quản trị bài, quản lý phiên — commit `33fe7eb`, `f98b976`, `acc9f02`, `1297a35`, `94b6a5f` |
| | Huy hiệu HIT/MISS và thời gian phản hồi trên trang chi tiết — commit `b95673c` |
| **CHƯA LÀM (phần đo hiệu năng)** | `scripts/Benchmark/benchmark.py` **vẫn là khung rỗng 33 dòng**, nội dung chỉ là ghi chú `# TODO [SV3]` và một dòng in ra chữ "TODO" |
| | **Không có commit nào** mang mã SCRUM-40 (đo tải), SCRUM-41 (biểu đồ so sánh), SCRUM-42 (chương kiểm thử hiệu năng) |
| | Cũng chưa có commit cho SCRUM-43 (kiểm thử hồi quy), SCRUM-44 (slide), SCRUM-45 (tổng duyệt demo) |

> **Lưu ý không được nhầm:** bộ test giao diện bằng Vitest của SV3 (11 file, 101 ca) là
> **test chức năng**, không phải đo hiệu năng — không thay thế được phần còn thiếu.

> **Câu chốt mục 4:** Ba trong bốn phần đã có bài làm; phần đo hiệu năng là chỗ hổng duy
> nhất và cũng là chỗ mất điểm lớn nhất.

---

## 5. Từng thành viên đã làm gì

### 5.1 Hồ Ngọc Phương Như — SV1, Kiến trúc dữ liệu & CRUD (nhóm trưởng)

**Đã xong:**

- **Toàn bộ phần tài khoản.** Đăng ký có mã hóa mật khẩu bằng BCrypt, chặn trùng tên đăng
  nhập ở **cả hai tầng** (kiểm tra trong mã và ràng buộc duy nhất ở cơ sở dữ liệu). Đăng
  nhập tạo phiên trên Redis và đặt cookie. Một chi tiết bảo mật: **sai tên đăng nhập và
  sai mật khẩu trả về cùng một thông báo**, để kẻ tấn công không dò được tài khoản nào có
  thật. *(`Controllers/AuthController.cs`)*
- **Toàn bộ CRUD bài viết và chuyên mục.** Gồm phân trang, lọc chuyên mục, sinh đường dẫn
  thân thiện tự động không trùng, xóa mềm, và kiểm tra chuyên mục có tồn tại thật trước
  khi gán. *(`Controllers/PostsController.cs`, `CategoriesController.cs`)*
- **Quy tắc ai được sửa bài.** Quản trị viên sửa được mọi bài; người thường chỉ sửa bài
  mình viết. 100 bài nạp mẫu không có tác giả nên **chỉ quản trị viên động vào được** —
  đây là thiết kế có chủ ý, không phải lỗi.
- **Trang quản lý phiên cho quản trị viên.** Liệt kê các phiên đang sống kèm thời gian còn
  lại, và buộc đăng xuất một phiên. Dùng lệnh quét theo con trỏ (`SCAN`) **chứ không dùng
  `KEYS`**, vì `KEYS` quét toàn bộ dữ liệu trong một lệnh và **làm nghẽn Redis**.
  *(`Services/RedisSessionQueryService.cs`)*
- **Chốt hợp đồng dữ liệu cho cả nhóm.** Quy ước camelCase, bảng key Redis, và đặt tài
  liệu vào đúng chỗ mà công cụ AI của ba người tự đọc được — vì cả nhóm dùng AI để viết
  mã, nhắn tin cho nhau không hiệu quả. *(`AGENTS.md` và các file `CLAUDE.md`)*
- **Ba tài liệu thiết kế** *(`docs/mongodb-schema.md`, `docs/redis-keyspace.md`,
  `docs/chot-thiet-ke-sv1.md`)* và **checklist đối chiếu barem**
  *(`docs/checklist-barem.md`)*.
- **Rà soát cài đặt từ máy sạch ngày 23/10:** phát hiện và sửa lỗi hai MongoDB cùng tranh
  một cổng, phát hiện 10 chỗ thiếu trong hướng dẫn cài đặt rồi viết lại.
  *(`docs/ra-soat-cai-dat-tu-dau.md`)*

**Còn lại:** viết chương thiết kế mô hình dữ liệu Redis thành báo cáo (thiếu sơ đồ và ảnh
chụp bằng chứng) · chuẩn bị trả lời phản biện · đóng gói nộp bài.

### 5.2 Nguyễn Anh Quân — SV2, Truy vấn nâng cao

**Đã xong:**

- **Lớp chặn kiểm tra phiên.** Mỗi yêu cầu đi qua đều được đọc phiên từ Redis và **gia hạn
  thời gian sống**, nên người dùng còn hoạt động thì không bị đăng xuất đột ngột.
  *(`Middleware/SessionAuthMiddleware.cs`)*
- **Luồng Cache-Aside hoàn chỉnh kèm khóa chống dồn.** Khi nhiều người cùng mở một bài vừa
  hết hạn cache, chỉ **một** yêu cầu được đi hỏi MongoDB, số còn lại chờ rồi đọc lại cache.
  *(`PostsController.GetById`, `Services/RedisCacheService.cs`)*
- **Bộ đếm lượt xem thời gian thực và tiến trình nền ghi về MongoDB.**
  *(`Services/ViewCountSyncWorker.cs`)*
- **Cache danh sách theo số phiên bản.** *(`PostsController.GetAll`)*
- **Bộ test tự động** bằng xUnit, dùng đối tượng giả nên không cần Redis/MongoDB chạy —
  6 file. *(`tests/NewsCacheSession.Tests/`)*
- **Báo cáo nguyên lý Cache-Aside** — phần 1,0 điểm của barem.
  *(`docs/bao-cao-nguyen-ly-cache-aside.md`)*

**Còn lại:** điền số đo thật vào chương kết quả thực nghiệm (chờ SV3) · chốt cách xử lý
lệch phiên bản .NET giữa dự án test và dự án API.

### 5.3 Nguyễn Xuân Định — SV3, Tích hợp & Kiểm thử

**Đã xong:**

- **Toàn bộ giao diện web.** Trang chủ kiểu báo điện tử có khu tin nổi bật và thanh chuyên
  mục, trang chi tiết bài, đăng nhập/đăng ký, trang soạn và sửa bài, trang quản trị bài
  viết, trang quản lý phiên.
- **Huy hiệu HIT/MISS kèm thời gian phản hồi** trên trang chi tiết — đây chính là thứ dùng
  để trình diễn trước thầy. *(`components/CacheStatusBadge.jsx`)*
- **Bộ script nạp dữ liệu mẫu:** 100+ bài viết có ảnh, kèm công cụ lấy tin thật và phân
  loại chuyên mục; và script nạp 20–50 phiên/cache key có thời hạn khác nhau.
  *(`scripts/SeedPosts/`, `scripts/SeedRedis/`)*
- **Bộ test giao diện:** 11 file, 101 ca, **chạy ngày 23/10 đạt toàn bộ**.

**Còn lại — đây là phần gấp nhất của cả nhóm:**

- **Viết script đo hiệu năng** (hiện mới là khung rỗng)
- **Vẽ biểu đồ so sánh thời gian tải** và lập bảng số liệu
- **Viết chương kiểm thử hiệu năng**
- Kiểm thử hồi quy toàn hệ thống · làm slide · tổng duyệt demo và quay video dự phòng

---

## 6. Kết quả hiện có — những gì demo được ngay hôm nay

Tất cả các mục dưới đây **đã tự chạy thử thành công ngày 23/10/2026** trên máy SV1 và được
ghi lại trong `docs/ra-soat-cai-dat-tu-dau.md`. Mã nguồn tương ứng được đánh dấu bằng thẻ
git `v0.9.0-demo-ok`.

### 6.1 Hệ thống khởi động được

| Kiểm tra | Kết quả |
|---|---|
| Ba container (MongoDB, Redis, RedisInsight) | **Chạy** |
| Trang kiểm tra sức khỏe `/health` | **Healthy** cả MongoDB lẫn Redis |
| Giao diện tại cổng 3000 | **HTTP 200** |

### 6.2 Dữ liệu đạt định mức đề bài

| Yêu cầu đề bài | Thực tế đo được | Đạt |
|---|---|---|
| MongoDB tối thiểu 100 bài có ảnh | **101 bài**, 5 chuyên mục | ✅ |
| Redis 20–50 session/cache key, thời hạn khác nhau | **41 key** — 21 phiên kiểu Hash + 20 cache | ✅ |
| Thời hạn khác nhau | Đo được: 454s · 768s · 1083s · 1321s · 1480s … | ✅ |

Soi thẳng MongoDB cũng xác nhận **hợp đồng dữ liệu được giữ đúng**: 100/100 bài có
`categoryId` đúng kiểu ObjectId (không có bài nào lưu nhầm thành chuỗi), tên trường đúng
camelCase, và **đủ 5 chỉ mục** được tạo tự động lúc khởi động.

### 6.3 Kịch bản demo — đã chạy đạt

| Bước | Thao tác | Kết quả thật |
|---|---|---|
| **1** | Mở một bài lần đầu | `X-Cache: MISS` |
| | Mở lại lần 2, lần 3 | `X-Cache: HIT` |
| | Soi Redis | Key `post:{id}` tồn tại, **thời hạn còn 599 giây** (đúng 10 phút) |
| **2** | **Sửa nội dung bài** | Soi Redis: key `post:{id}` **đã biến mất** |
| | Mở lại bài | `X-Cache: MISS`, và **trả về nội dung mới** |
| **3** | Xem 3 lượt | Bộ đếm `post:{id}:views` = **3**, thời hạn = **không hết hạn** |
| | Danh sách bài | Lần 1 MISS, lần 2 HIT; key sinh ra đúng dạng `posts:cat:all:p1:v14` |

Các chức năng khác cũng đã thử đạt: tài khoản đầu tiên tự thành quản trị viên; sai tên
đăng nhập và sai mật khẩu trả **cùng một thông báo**; sinh đường dẫn thân thiện từ tiêu đề
tiếng Việt có dấu (*"Đội tuyển Việt Nam thắng đậm"* → `doi-tuyen-viet-nam-thang-dam`).

### 6.4 Về số đo hiệu năng — phải nói rõ ràng

**Bộ đo hiệu năng chính thức chưa tồn tại.** Script đo vẫn là khung rỗng, chưa có biểu đồ,
chưa có bảng số liệu, chưa có chương kiểm thử hiệu năng.

Ngày 23/10 nhóm có **đo thử nhanh** trong lúc rà soát cài đặt — 15 lượt mỗi loại, cơ sở dữ
liệu 101 bài, chạy trên **một máy cá nhân**:

| Phép đo | Lấy từ MongoDB | Lấy từ Redis | Chênh |
|---|---|---|---|
| Chi tiết một bài | 11,0 ms | 4,4 ms | **2,5 lần** |
| Danh sách 20 bài | 20,0 ms | 8,0 ms | **2,5 lần** |

**Đây là con số đo thật, nhóm xin báo cáo đúng như đo được.** Nhóm lưu ý hai điểm:

1. Đề bài mô tả demo là *"lần 1 khoảng 200ms, lần 2 dưới 5ms"*. **Nhóm chưa đạt mức chênh
   lệch đó.** Lý do: MongoDB chạy ngay trên máy, dữ liệu còn nhỏ và đã có chỉ mục nên đọc
   rất nhanh; phần lớn 4,4 ms của lượt HIT là chi phí truyền qua HTTP chứ không phải do
   Redis chậm.
2. Nhóm **không chỉnh số cho đẹp**. Cách làm cho khác biệt hiện rõ một cách trung thực là
   **tăng quy mô dữ liệu** (script hỗ trợ nạp 1.000+ bài) và **đo dưới tải đồng thời**
   thay vì đo từng yêu cầu lẻ. Đó chính là nội dung phần còn thiếu của SV3.

> **Câu chốt:** Ba bước demo đều chạy đạt; riêng số đo hiệu năng mới ở mức thử nhanh, bộ đo
> chính thức là việc còn lại.

---

## 7. Việc còn lại — kế hoạch giai đoạn tiếp theo

### 7.1 Việc sẽ làm tiếp

| Việc | Ai | Hạn | Điểm liên quan |
|---|---|---|---|
| **Viết script đo, vẽ biểu đồ, viết chương kiểm thử hiệu năng** | **SV3 Định** | 24/10 | **~1,0–1,5đ** |
| **Chương thiết kế Redis: bổ sung sơ đồ luồng + ảnh chụp RedisInsight** | **SV1 Như** | 24/10 | **1,5đ** |
| Điền số đo thật vào chương kết quả thực nghiệm | SV2 Quân | sau khi có số | trong 1,0đ |
| Chốt xử lý lệch phiên bản .NET của dự án test | SV2 Quân | 24/10 | bảo vệ bằng chứng kiểm thử |
| Nạp lại dữ liệu sạch trên máy dùng để demo | SV3 Định | 24/10 | bảo vệ 1,0đ |
| Kiểm thử hồi quy, slide, tổng duyệt demo, quay video dự phòng | cả nhóm | 25/10 | 1,5đ |
| Chuẩn bị trả lời phản biện phần của mình | mỗi người | 25/10 | — |
| Đóng gói và nộp | SV1 Như | 26/10 | — |

**Mốc chặn:** từ **trưa 25/10 không thêm tính năng mới**, chỉ sửa lỗi và tổng duyệt.

### 7.2 Rủi ro, xếp theo mức nghiêm trọng

| # | Rủi ro | Mức | Cách xử lý |
|---|---|---|---|
| 1 | **Phần đo hiệu năng chưa có gì.** Đây vừa là ~1,0–1,5đ của barem, vừa là **bước 1 của kịch bản demo** | 🔴 Cao nhất | Làm bản tối thiểu trước: gọi hai đường đọc (có cache / không cache) mỗi bên 20 lần, ghi lại mili giây, vẽ một biểu đồ cột. **Ước 2 giờ, không cần công cụ đo tải chuyên dụng.** Có dư thời gian mới nâng cấp |
| 2 | **Chênh lệch tốc độ chưa ấn tượng như đề bài mô tả** (2,5 lần thay vì ~40 lần) | 🟠 | Không sửa số. Nâng quy mô dữ liệu và đo dưới tải đồng thời. Khi trình bày thì **giải thích đúng nguyên nhân** thay vì né |
| 3 | **Chương thiết kế Redis chưa có sơ đồ và ảnh bằng chứng** — thầy chấm 1,5đ bằng cách đối chiếu tài liệu với RedisInsight | 🟠 | Chụp 4 ảnh: phiên đang đếm lùi, bản ghi nhớ bài viết còn hạn, bộ đếm lượt xem tăng, số phiên bản tăng sau khi sửa bài. Vẽ 1 sơ đồ luồng đọc |
| 4 | **`dotnet test` hỏng lúc biên dịch** trên máy chỉ có SDK 9 | 🟠 | Chốt một trong hai: cài SDK 10, hoặc hạ cấu hình dự án test. **Nếu không xử lý, máy demo không chạy được test là mất bằng chứng kiểm thử của SV2** |
| 5 | Phần CRUD **không có test tự động**, chỉ kiểm tay và nhật ký không nằm trong repo | 🟡 | Khi báo cáo nói đúng là "kiểm thủ công", không nói là "có bộ test". Dư thời gian thì đưa kịch bản kiểm vào repo |
| 6 | Cơ sở dữ liệu hiện còn lẫn dữ liệu thử nghiệm | 🟡 | Trước demo xóa sạch rồi nạp lại |

> **Câu chốt mục 7:** Mã nguồn đã gần đủ điểm; chỗ mất điểm còn lại nằm ở **hai tài liệu
> chưa viết**, không nằm ở phần lập trình.

---

## 8. Gợi ý cho người dựng slide

Đề xuất **12 slide**. Mỗi slide ghi: tiêu đề · câu chính · ý phụ · mô tả hình minh họa.

---

**Slide 1 — Trang bìa**
*Câu chính:* Đề tài 06 — Caching bài viết và Quản lý phiên bằng Redis + MongoDB.
*Ý phụ:* Tên môn, tên 3 thành viên kèm vai trò, ngày 23/10/2026, hạn nộp 26/10/2026.
*Hình:* Nền đơn sắc. Hai khối tròn nối nhau bằng mũi tên hai chiều, một ghi "MongoDB", một
ghi "Redis".

---

**Slide 2 — Bài toán, giải thích bằng hình ảnh đời thường**
*Câu chính:* Vào kho lấy sách thì chậm; để sẵn trên bàn thì nhanh.
*Ý phụ:* Kho lớn = MongoDB (lưu thật, chậm hơn) · Bàn nhỏ ngay cửa = Redis (lưu tạm,
nhanh) · Một bài nổi tiếng bị hỏi hàng nghìn lần thì không nên vào kho hàng nghìn lần.
*Hình:* Tranh hai cảnh cạnh nhau. Trái: người thủ thư đi sâu vào dãy kệ dài. Phải: người
thủ thư với tay lấy cuốn sách trên bàn ngay cửa. Dùng đồng hồ nhỏ ở mỗi cảnh để gợi ý
nhanh/chậm, **không ghi con số**.

---

**Slide 3 — Sản phẩm là gì**
*Câu chính:* Một trang báo điện tử có phần quản trị, chạy trên MongoDB và Redis.
*Ý phụ:* Trang chủ có khu tin nổi bật, thanh chuyên mục, danh sách bài chia trang · Trang
chi tiết có nội dung và số lượt xem · Người đăng nhập viết bài, quản trị viên quản lý bài
và phiên · Phạm vi đồ án tập trung vào caching và quản lý phiên.
*Hình:* Ảnh chụp màn hình trang chủ thật của dự án.

---

**Slide 4 — Kiến trúc tổng quan**
*Câu chính:* Trình duyệt → API (có lớp chặn kiểm tra phiên) → Redis trước, MongoDB sau.
*Ý phụ:* Bốn tầng · Một tiến trình nền ghi lượt xem về MongoDB mỗi phút · Một máy chủ
Redis duy nhất.
*Hình:* Sơ đồ khối ngang 4 ô nối bằng mũi tên: Trình duyệt → API → Redis → MongoDB. Vẽ một
ô nhỏ phía dưới API ghi "Lớp chặn kiểm tra phiên" có mũi tên chỉ lên Redis. Một ô rời bên
dưới ghi "Tiến trình nền — mỗi 1 phút" nối Redis với MongoDB.

---

**Slide 5 — Luồng Cache-Aside**
*Câu chính:* Hỏi Redis trước; chỉ một yêu cầu được phép đi hỏi MongoDB.
*Ý phụ:* Có sẵn → trả ngay (HIT) · Không có → giành khóa 5 giây → kiểm tra lại → đọc
MongoDB → ghi vào Redis (MISS) · Không giành được khóa → chờ 50 mili giây rồi thử lại.
*Hình:* Sơ đồ luồng có nhánh rẽ. Nhánh HIT tô một màu, nhánh MISS tô màu khác. Vẽ thêm
hình ổ khóa nhỏ ở bước giành khóa.

---

**Slide 6 — Bảng các key Redis**
*Câu chính:* Mỗi loại dữ liệu một cấu trúc và một thời hạn, đều có lý do.
*Ý phụ:* Dùng **nguyên bảng ở mục 3.4** · Nhấn mạnh: phiên dùng Hash vì cần sửa từng phần;
bài viết dùng String vì dùng nguyên khối; bộ đếm lượt xem không hết hạn.
*Hình:* Chính cái bảng. Tô nền khác màu cho cột "Thời gian sống" để mắt bắt vào trước.

---

**Slide 7 — Hai quyết định thiết kế đáng nói nhất**
*Câu chính:* Xóa cả một nhóm cache bằng một lệnh tăng số; khóa chống dồn bắt buộc có hạn.
*Ý phụ:* Danh sách bài rải ra rất nhiều key — quét xóa từng cái thì tốn, gắn số phiên bản
vào tên key thì chỉ cần một lệnh · Đánh đổi: tối đa 3 phút tốn thêm bộ nhớ · Khóa không có
hạn mà tiến trình chết giữa chừng là chặn mọi yêu cầu vĩnh viễn.
*Hình:* Bên trái vẽ nhiều ô key xếp chồng có dấu X đỏ lên từng ô (cách cũ). Bên phải vẽ
một mũi tên duy nhất vào ô "số phiên bản +1", các ô cũ mờ dần đi (cách đã chọn).

---

**Slide 8 — Tiến độ theo barem**
*Câu chính:* Ba trong bốn phần đã có bài làm; phần đo hiệu năng là chỗ hổng duy nhất.
*Ý phụ:* Bảng 4 dòng ở **mục 4**, kèm trạng thái xong / một phần / chưa làm.
*Hình:* Bốn thanh tiến độ ngang, mỗi thanh ghi tên phần và 2,5đ. Ba thanh gần đầy, thanh
"Kiểm thử hiệu năng & Demo" vơi rõ rệt và tô màu cảnh báo.

---

**Slide 9 — Phân công và kết quả từng người**
*Câu chính:* Ba người, ba mảng tách bạch, không ai chặn ai.
*Ý phụ:* Như — thiết kế dữ liệu + CRUD + xác thực + phân quyền · Quân — cache, phiên, bộ
đếm, test tự động · Định — giao diện, dữ liệu mẫu, kiểm thử. Mỗi người kèm **1 dòng việc
còn lại**.
*Hình:* Ba cột dọc, mỗi cột một người, phía dưới mỗi cột có một dải nhỏ ghi "Còn lại".

---

**Slide 10 — Demo được ngay hôm nay**
*Câu chính:* Ba bước demo đều đã chạy thử đạt.
*Ý phụ:* Mở bài lần 1 MISS → lần 2 HIT · Sửa bài → key cache biến mất → mở lại thấy nội
dung mới · Phiên có thời hạn đếm lùi · Dữ liệu đạt định mức: 101 bài, 41 key Redis.
*Hình:* Ba ảnh chụp màn hình thật xếp ngang: huy hiệu MISS, huy hiệu HIT, và cửa sổ
RedisInsight thấy key cùng thời hạn còn lại.

---

**Slide 11 — Nói thật về số đo** *(slide quan trọng, đừng bỏ)*
*Câu chính:* Nhóm đo được chênh 2,5 lần, chưa đạt mức đề bài mô tả, và xin báo cáo đúng
như vậy.
*Ý phụ:* Bảng số đo thử ở **mục 6.4** · Nguyên nhân: dữ liệu còn nhỏ, MongoDB chạy ngay
trên máy, đã có chỉ mục · Bộ đo chính thức **chưa làm** · Hướng xử lý: tăng quy mô dữ liệu
và đo dưới tải đồng thời, **không chỉnh số**.
*Hình:* Biểu đồ cột đơn giản, hai cặp cột (chi tiết bài, danh sách bài), mỗi cặp một cột
"MongoDB" một cột "Redis". **Chỉ vẽ đúng 4 con số có thật.** Dưới biểu đồ ghi rõ dòng chữ
"đo thử, 15 lượt/loại, 101 bài, trên một máy cá nhân".

---

**Slide 12 — Việc còn lại và rủi ro**
*Câu chính:* Chỗ mất điểm còn lại nằm ở hai tài liệu chưa viết, không nằm ở phần lập trình.
*Ý phụ:* Hai việc gấp nhất: bộ đo hiệu năng (Định) và chương thiết kế Redis có ảnh bằng
chứng (Như) · Mốc chặn: trưa 25/10 không thêm tính năng mới · Hạn nộp 26/10.
*Hình:* Dòng thời gian ngang từ 23/10 đến 26/10, gắn các mốc việc. Đánh dấu rõ điểm "chốt
không thêm tính năng" ở trưa 25/10.

---

## 9. Điều chưa chắc hoặc chưa kiểm chứng được

Tài liệu này bám **barem 4 phần × 2,5 điểm của đề bài gốc**. Mọi trạng thái ở mục 4 phản
ánh đúng những gì đang có trong mã nguồn tại ngày 23/10/2026; phần chưa có được đưa sang
mục 7 thành kế hoạch giai đoạn tiếp theo. Bốn điểm dưới đây nên nói đúng như vậy nếu được
hỏi:

1. **Mô tả công việc của SV2 và SV3** trong mục 5 dựa trên **thông điệp commit, tên file và
   giao diện**, không phải đọc kỹ từng dòng mã của hai bạn. Hai bạn nên tự đọc lại khối
   của mình.
2. **Số đo ở mục 6.4** là đo nhanh trong lúc rà soát cài đặt, **không phải một phép đo được
   thiết kế bài bản**: chạy trên một máy cá nhân, không kiểm soát tiến trình nền, không
   lặp nhiều đợt, không tính độ lệch. Nếu thầy hỏi phương pháp đo thì phải trả lời đúng
   như vậy.
3. **Kết quả kiểm thử phần CRUD.** Nhóm có ghi nhận một đợt kiểm tay 54 ca đạt toàn bộ vào
   ngày 30/09, nhưng **nhật ký và ảnh chụp của đợt đó không nằm trong repo**, và chưa chạy
   lại sau khi hai bạn kia gộp thêm mã. Tài liệu này **không dùng con số 54 đó** làm bằng
   chứng.
4. **Mô tả sản phẩm ở mục 2.1** dựa trên giao diện và mã nguồn thật trong repo tại thời
   điểm 23/10. Nếu nhóm dự định bổ sung chức năng mới sau mốc này thì phải nói rõ đó là
   **dự định**, không phải hiện trạng.
