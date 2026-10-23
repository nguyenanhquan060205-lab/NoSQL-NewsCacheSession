# Kịch bản trình bày phần SV1 — Hồ Ngọc Phương Như

**Vai:** Data Architect & CRUD Lead — thiết kế mô hình dữ liệu và viết API nền tảng.
**Phần điểm phụ trách:** 1,5đ (thiết kế mô hình Hashes/Strings + cơ chế khóa) + 2,5đ
(chức năng CRUD nền tảng) = **4/10 điểm của cả nhóm**.

> **Cách dùng:** phần 1 là bài nói khoảng 8 phút. Phần 2 là ngân hàng câu hỏi phản biện.
> Đọc phần 2 kỹ hơn phần 1 — thầy chấm thiết kế bằng câu hỏi, không bằng bài thuyết trình.

---

# PHẦN 1 — Bài nói

## Mở đầu (30 giây)

> Em là Hồ Ngọc Phương Như, phụ trách vai Data Architect và CRUD Lead.
>
> Phần của em trả lời hai câu hỏi: **dữ liệu nằm ở đâu**, và **khi nào thì bản sao trong
> bộ nhớ đệm trở nên sai**. Em sẽ trình bày ba tầng: thiết kế MongoDB, thiết kế keyspace
> Redis, và các luật nghiệp vụ em cài vào API.

## Tầng 1 — Thiết kế MongoDB (2 phút)

> MongoDB là **nguồn sự thật** của đồ án. Em thiết kế ba collection: `posts`, `users`,
> `categories`.
>
> **Quyết định đầu tiên, và cũng là lỗi nặng nhất em phát hiện được: tên field phải là
> camelCase, ép bằng thuộc tính `[BsonElement]` trên từng property.**
>
> Vì sao quan trọng? Thư viện MongoDB.Driver của C# **mặc định lấy đúng tên property**,
> tức là PascalCase — `Title`, `CreatedAt`. Nhưng script seed của bạn Định viết bằng
> Python thì ghi camelCase — `title`, `createdAt`. Hai bên lệch nhau thì chuyện xảy ra
> rất khó chịu: **lệnh ghi vẫn thành công, không báo lỗi gì cả**, nhưng khi API đọc lên
> thì bài viết **rỗng tiêu đề** và ngày tạo thành **01/01/0001**. Trang chủ trắng, sắp
> xếp sai, và mất luôn 1 điểm dữ liệu mẫu.
>
> Em chọn camelCase chứ không phải snake_case như bản thiết kế đầu, vì camelCase khớp
> luôn với JSON trả về cho frontend — một quy ước dùng được cho cả ba nơi.
>
> **Quyết định thứ hai: dùng tham chiếu, không nhúng.** `categoryId` và `authorId` lưu
> dạng ObjectId trỏ sang collection khác. Nếu nhúng cả object chuyên mục vào từng bài
> viết thì đổi tên "Thể thao" thành "Thể dục thể thao" phải cập nhật hàng chục bài.
> Đánh đổi là đọc bài kèm tên chuyên mục cần thêm một truy vấn — nhưng với luồng
> Cache-Aside thì chi phí đó **trả một lần rồi nằm trong Redis**.
>
> **Quyết định thứ ba: xóa mềm.** Xóa bài chỉ đánh dấu `isDeleted`, dữ liệu vẫn còn.
> Và khi lọc bài chưa xóa, em dùng `Ne(isDeleted, true)` **chứ không phải**
> `Eq(isDeleted, false)`. Lý do: 100 bài seed **không có field `isDeleted`**, mà field
> không tồn tại thì không "bằng false" — dùng `Eq` là mất sạch 100 bài.

## Tầng 2 — Thiết kế keyspace Redis (3 phút, trọng tâm)

> Đây là phần 1,5 điểm của em.
>
> **Nguyên tắc em dựa vào để chọn cấu trúc dữ liệu là: truy cập từng phần thì dùng Hash,
> truy cập nguyên khối thì dùng String.**
>
> Một **phiên đăng nhập** gồm nhiều mẩu nhỏ: `userId`, `username`, `role`, `loginAt`,
> `lastActive`. Middleware nhiều khi chỉ cần đúng một mẩu. Và em cần cập nhật riêng
> `lastActive` mà **không phải đọc cả phiên ra, sửa, rồi ghi lại**. Hash làm được đúng
> việc đó. Đề bài cũng yêu cầu rõ dùng Hash cho session, nhưng kể cả không có yêu cầu đó
> thì lý do kỹ thuật vẫn đứng vững.
>
> **Bài viết** thì ngược lại — luôn đọc, ghi, xóa nguyên khối. Chưa bao giờ cần lấy riêng
> cái tiêu đề ra khỏi cache. Nên String JSON là đơn giản và nhanh nhất, và một lệnh
> `SET key value EX 600` làm được cả ghi lẫn đặt hạn.
>
> **Bộ đếm lượt xem em tách thành một key String riêng** — `post:{id}:views`. Ba lý do,
> xếp theo độ nặng: thứ nhất, lệnh `INCR` **chỉ chạy trên String**, không chạy được trên
> một field bên trong JSON. Thứ hai, tăng lượt xem không phải đọc rồi ghi lại cả bài.
> Thứ ba, và quan trọng nhất: cache nội dung hết hạn sau 10 phút, **bộ đếm thì không
> được mất**.
>
> **Về thời gian sống, mỗi loại một con số và đều có lý do:**
>
> - Phiên 30 phút, tự gia hạn — đủ dài để không bị đăng xuất giữa lúc soạn bài, đủ ngắn
>   để tự hết nếu bỏ máy.
> - Bài viết 10 phút. Ở đây em muốn nhấn một ý: **TTL chính là lưới an toàn cho cơ chế
>   xóa cache.** Nếu Redis mất kết nối đúng lúc sửa bài, lệnh xóa cache không tới nơi,
>   thì dữ liệu cũ cũng chỉ sống được tối đa 10 phút chứ không sống mãi.
> - Danh sách 3 phút — vì danh sách thay đổi thường xuyên nhất.
> - Bộ đếm lượt xem và `posts:ver` thì **không đặt hạn**. `posts:ver` mà hết hạn rồi quay
>   về 0 thì các key cache cũ mang số lớn hơn có thể bị tra lại, tức là đọc nhầm dữ liệu
>   cũ.
>
> **Đóng góp em tâm đắc nhất là cách xóa cache danh sách.**
>
> Cache một bài chỉ có một key, xóa thẳng là xong. Nhưng cache danh sách rải ra **rất
> nhiều key** — mỗi chuyên mục nhân mỗi số trang. Cách thường thấy là `SCAN` tìm hết rồi
> `DEL` từng cái. Cách đó tốn thời gian **tỉ lệ với số key**, phải lặp nhiều lượt, và còn
> phải thêm một hàm mới vào file của bạn Quân.
>
> Em làm khác: **gắn số phiên bản vào chính tên key** —
> `posts:cat:{categoryId}:p{page}:v{ver}`. Mỗi lần dữ liệu đổi, em chỉ cần **một lệnh
> `INCR posts:ver`**. Các key cũ mang số nhỏ hơn thì **không còn ai tra tới nữa** và tự
> biến mất khi hết hạn 3 phút. Từ O(N) xuống **O(1)**.
>
> Mẫu này tên là *cache key versioning*, hay *generational caching*.
>
> **Đánh đổi em xin nói luôn:** trong tối đa 3 phút, Redis giữ cả bản cũ lẫn bản mới nên
> tốn thêm bộ nhớ. Với danh sách bài viết thì không đáng kể.

## Tầng 3 — Luật nghiệp vụ trong API (1,5 phút)

> **Luật quan trọng nhất: ghi MongoDB trước, xóa Redis sau.**
>
> Nếu làm ngược lại — xóa cache trước rồi mới ghi database — thì có một khe hở: một yêu
> cầu đọc chen vào đúng giữa hai thao tác sẽ **nạp lại đúng dữ liệu cũ** vào cache, và
> giữ nó thêm **trọn một vòng TTL**. Thứ tự này không phải tùy tiện.
>
> **Về phân quyền:** quản trị viên sửa được mọi bài, người thường chỉ sửa bài mình viết.
> 100 bài seed có `authorId` là null nên **chỉ quản trị viên động vào được**. Trước đó
> code cũ cho bất kỳ ai đăng nhập cũng xóa được cả 100 bài seed.
>
> **Em không cài sẵn tài khoản admin** mà để **người đăng ký đầu tiên tự động thành
> admin**. Lý do: cài sẵn là để lộ mật khẩu quản trị trong file cấu hình.
>
> **Một chi tiết bảo mật nhỏ:** sai tên đăng nhập và sai mật khẩu em trả về **cùng một
> thông báo**. Nếu tách hai thông báo, kẻ tấn công dò được tài khoản nào có thật.
>
> **Khi liệt kê phiên cho trang quản trị em dùng `SCAN`, không dùng `KEYS`.** `KEYS` quét
> toàn bộ keyspace trong một lệnh và **chặn Redis** — Redis xử lý lệnh tuần tự trên một
> luồng, nên trong lúc đó mọi yêu cầu khác phải chờ.

## Chứng minh bằng demo (1 phút)

> Em xin chứng minh phần thiết kế chạy đúng như mô tả.
>
> *(Mở RedisInsight)* Đây là key `post:{id}` — kiểu String, hạn còn khoảng 600 giây, đúng
> 10 phút như thiết kế. Đây là `session:{id}` — kiểu **Hash**, bên trong có đủ `userId`,
> `username`, `role`, và hạn đang đếm ngược từ 1800 giây.
>
> *(Sửa một bài viết)* Em sửa nội dung bài này... và bây giờ làm mới RedisInsight —
> **key `post:{id}` đã biến mất**. Tải lại trang thì huy hiệu hiện MISS và nội dung là bản
> vừa sửa.
>
> *(Chỉ vào posts:ver)* Và số phiên bản danh sách vừa tăng thêm một.

## Kết (30 giây)

> Tóm lại, phần của em là **ba tầng quyết định**: chọn cách lưu trong MongoDB, chọn cấu
> trúc và thời gian sống trong Redis, và cài các luật đảm bảo dữ liệu không bao giờ cũ.
>
> Mỗi quyết định em đều ghi lý do trong tài liệu `docs/redis-keyspace.md` và
> `docs/mongodb-schema.md`. Em xin hết.

---

# PHẦN 2 — Ngân hàng câu hỏi phản biện

Đọc phần này kỹ hơn phần trên. Mỗi câu có **ý cốt lõi** (bắt buộc nói) và **ý cộng điểm**
(nói nếu còn thời gian).

### 1. Vì sao session dùng Hash mà cache bài viết dùng String?

**Cốt lõi:** Phiên gồm nhiều mẩu nhỏ, cần đọc riêng một mẩu và sửa riêng `lastActive` mà
không phải đọc–ghi lại cả phiên → Hash. Bài viết luôn dùng nguyên khối → String đơn giản
và nhanh hơn.
**Cộng điểm:** Nguyên tắc chung — truy cập từng phần thì Hash, truy cập nguyên khối thì
String. Và `SET key value EX 600` làm cả hai việc trong một lệnh.

### 2. Vì sao bộ đếm lượt xem phải là key riêng?

**Cốt lõi:** `INCR` chỉ chạy trên String, không chạy trên field trong JSON. Và cache nội
dung hết hạn sau 10 phút nhưng bộ đếm không được mất.
**Cộng điểm:** Em đổi tên từ `post_views:{id}` sang `post:{id}:views` để gom về cùng
namespace — một lệnh `SCAN post:*` lấy được cả nội dung lẫn bộ đếm của một bài.

### 3. Vì sao TTL bài viết là 10 phút, không phải 1 giờ?

**Cốt lõi:** TTL là **lưới an toàn** cho cơ chế xóa cache. Nếu lệnh xóa không tới nơi vì
Redis mất kết nối, 10 phút là mức sai lệch tối đa em chấp nhận. 1 giờ thì rủi ro quá lớn.
**Cộng điểm:** Ngắn quá thì tỉ lệ trúng cache thấp, cache mất tác dụng. 10 phút là chỗ cân
bằng.

### 4. Bỏ `PX 5000` khỏi lệnh khóa thì sao?

**Cốt lõi:** Nếu tiến trình đang giữ khóa chết giữa chừng mà khóa không tự hết hạn thì
**mọi yêu cầu sau đó bị chặn vĩnh viễn**. Đây là lỗi kinh điển khi tự viết khóa phân tán.
**Cộng điểm:** 5 giây đủ cho một truy vấn MongoDB và dư an toàn.

### 5. Vì sao lọc `Ne(isDeleted, true)` chứ không `Eq(isDeleted, false)`?

**Cốt lõi:** Document cũ và dữ liệu seed **chưa có field `isDeleted`**. Trong MongoDB,
field không tồn tại thì không "bằng false", nên `Eq` loại sạch những document đó.
`Ne(..., true)` khớp cả document thiếu field.

### 6. Vì sao sửa bài phải ghi MongoDB trước rồi mới xóa Redis?

**Cốt lõi:** Làm ngược lại thì một yêu cầu đọc chen vào giữa sẽ nạp lại đúng dữ liệu cũ
vào cache và giữ nó thêm trọn một vòng TTL.
**Cộng điểm:** Vẫn còn một khe hở rất nhỏ ngay sau khi ghi xong mà chưa kịp xóa — đó là
lý do TTL tồn tại. Nhóm ghi nhận đây là đánh đổi có ý thức.

### 7. Vì sao dùng số phiên bản mà không SCAN rồi DEL?

**Cốt lõi:** Cache danh sách rải ra nhiều key (chuyên mục × số trang). SCAN+DEL là O(N),
phải lặp nhiều lượt. Gắn số phiên bản vào tên key thì chỉ cần một lệnh `INCR` — O(1).
**Cộng điểm:** Tên mẫu là *cache key versioning*. Đánh đổi: tối đa 3 phút tốn thêm bộ nhớ
vì giữ cả bản cũ lẫn mới.

### 8. Vì sao `posts:ver` không đặt TTL?

**Cốt lõi:** Nếu nó hết hạn rồi quay về 0, các key cache cũ mang số lớn hơn có thể bị tra
lại → đọc nhầm dữ liệu cũ. Bộ đếm phiên bản mất đi là **sai nghiệp vụ**, không chỉ chậm.

### 9. Vì sao `ToSlug` phải xử lý riêng chữ `đ`?

**Cốt lõi:** `Normalize(FormD)` tách chữ và dấu thành hai ký tự rồi mình bỏ ký tự dấu đi.
Nhưng `đ` là **một ký tự Unicode độc lập**, không phải `d` cộng dấu, nên FormD không tách
được và nó bị biểu thức chính quy loại mất. Phải `.Replace('đ', 'd')` trước.
**Cộng điểm:** Không xử lý thì "Đội tuyển" ra slug `oi-tuyen`, mất chữ đầu.

### 10. Vì sao sai username và sai password lại trả cùng một thông báo?

**Cốt lõi:** Nếu tách hai thông báo, kẻ tấn công thử lần lượt sẽ **dò ra tài khoản nào có
thật** trong hệ thống, rồi tập trung phá mật khẩu tài khoản đó.

### 11. Vì sao không cài sẵn tài khoản admin?

**Cốt lõi:** Cài sẵn là để lộ mật khẩu quản trị trong file cấu hình, mà file đó nằm trong
repo. Em để người đăng ký đầu tiên tự thành admin.
**Cộng điểm:** Cấp quyền cho người khác về sau bằng lệnh cập nhật trực tiếp trong MongoDB.

### 12. Vì sao liệt kê phiên bằng `SCAN` mà không `KEYS`? Cách này mở rộng được không?

**Cốt lõi:** `KEYS` quét toàn bộ keyspace trong một lệnh và chặn Redis, vì Redis xử lý
tuần tự trên một luồng. `SCAN` đi bằng con trỏ, chia thành nhiều lượt nhỏ.
**Cộng điểm — câu trả lời cho "mở rộng được không":** Ở quy mô thật thì cách đúng là duy
trì thêm một Set `user_sessions:{userId}` để liệt kê mà không cần quét keyspace; đánh đổi
là phải cập nhật Set mỗi lần tạo hoặc xóa phiên. Với 20–50 phiên theo định mức đề bài thì
`SCAN` thừa sức.

### 13. Vì sao dùng tham chiếu mà không nhúng chuyên mục vào bài viết?

**Cốt lõi:** Nhúng thì đổi tên một chuyên mục phải cập nhật hàng chục bài. Tham chiếu thì
sửa một chỗ.
**Cộng điểm:** Đánh đổi là đọc bài kèm tên chuyên mục cần thêm một truy vấn — nhưng với
Cache-Aside thì chi phí đó trả một lần rồi nằm trong Redis.

### 14. Vì sao không cache luôn endpoint đọc theo slug?

**Cốt lõi:** Endpoint đó được **cố ý giữ nguyên** làm mốc đo "trước khi có cache", để so
sánh hiệu năng. Cache luôn cả nó thì mất đường đối chứng.

### 15. Tại sao xóa bài mà không xóa bộ đếm lượt xem?

**Cốt lõi:** Xóa mềm nghĩa là bài **có thể phục hồi**, và lượt xem là số liệu tích lũy.
Phải để tiến trình nền chốt số về MongoDB trước. Bản code đầu có xóa key này, em đã sửa.

### 16. Em tách `ISessionQueryService` khỏi `ISessionService` để làm gì?

**Cốt lõi:** `ISessionService` lo **vòng đời** một phiên — tạo, đọc, gia hạn, xóa.
`ISessionQueryService` chỉ **liệt kê** phiên cho trang quản trị. Tách theo hướng CQRS.
**Cộng điểm:** Lý do thực dụng là hai phần việc thuộc hai người nên không đụng cùng file.
Lý do thiết kế là phần quản trị sau này có thể thêm bộ lọc, phân trang mà không làm phình
interface đang dùng ở đường đi nóng.

---

## Ba câu khó, nếu bị hỏi thì trả lời thế này

**"Em có tự viết phần này không?"**
Trả lời trung thực: *"Em dùng công cụ AI hỗ trợ viết code, nhưng các quyết định thiết kế
là của em và em giải thích được từng cái. Thầy hỏi bất kỳ chỗ nào em cũng nói được vì sao
chọn như vậy và nếu chọn khác thì hỏng ở đâu."* — Rồi chứng minh bằng chính các câu trên.

**"Thiết kế này có chỗ nào em thấy chưa ổn?"**
*"Có ba chỗ: thứ nhất, liệt kê phiên bằng SCAN chỉ hợp quy mô nhỏ, quy mô thật nên dùng
thêm Set chỉ mục. Thứ hai, vẫn còn khe hở rất nhỏ giữa lúc ghi MongoDB xong và lúc xóa
Redis, TTL 10 phút là lưới an toàn cho khe hở đó. Thứ ba, phần CRUD của em chưa có test
tự động, mới kiểm thủ công."*

**"Nếu Redis sập thì sao?"**
*"Phần đọc bài vẫn chạy được vì MongoDB là nguồn sự thật, chỉ chậm đi. Nhưng phần đăng
nhập sẽ hỏng vì phiên lưu hoàn toàn trên Redis — đây là hạn chế nhóm em ghi nhận, chưa
làm chế độ suy giảm."*
