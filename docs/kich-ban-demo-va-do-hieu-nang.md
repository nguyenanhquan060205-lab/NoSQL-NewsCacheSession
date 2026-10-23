# Kịch bản demo và cách đo hiệu năng

**Viết ngày 23/10/2026.** Mọi lệnh trong file này **đã được chạy thử thật** trên máy SV1
và có kết quả thật kèm theo. Làm đúng từ trên xuống dưới, không cần bỏ qua bước nào.

> **Cách dùng file này.** Phần A làm trước (chuẩn bị máy). Phần B để lấy số đo và vẽ biểu
> đồ. Phần C là kịch bản đứng trước thầy. Phần D để tra khi có sự cố.

---

# PHẦN A — Chuẩn bị, tính từ lúc bấm nút mở máy

Mỗi bước có **"làm gì"** và **"thấy gì thì đúng"**. Chưa thấy đúng thì đừng sang bước sau.

## Bước 1 — Mở Docker Desktop

**Làm gì:**
1. Bấm phím `Windows` trên bàn phím.
2. Gõ chữ `Docker`.
3. Bấm `Enter` để mở **Docker Desktop**.
4. **Chờ khoảng 1–2 phút.**

**Thấy gì thì đúng:** góc dưới bên trái cửa sổ Docker Desktop có **hình con cá voi màu
xanh lá** và chữ **Engine running**. Nếu còn màu vàng và chữ *Starting* thì chờ tiếp.

> **Tại sao cần bước này:** Docker là cái "hộp" chứa sẵn MongoDB và Redis. Chưa mở hộp thì
> chưa có gì chạy.

## Bước 2 — Tắt MongoDB của Windows (chỉ máy nào có)

Một số máy cài sẵn MongoDB như một dịch vụ của Windows. Nó **giành mất chỗ** của MongoDB
trong Docker, làm chương trình đọc nhầm vào kho rỗng.

**Làm gì:**
1. Bấm phím `Windows`, gõ `powershell`.
2. **Bấm chuột phải** vào *Windows PowerShell* → chọn **Run as administrator**.
3. Bấm **Yes** khi máy hỏi.
4. Gõ đúng hai dòng sau, mỗi dòng xong bấm `Enter`:

```powershell
net stop MongoDB
Set-Service MongoDB -StartupType Manual
```

**Thấy gì thì đúng:** dòng chữ *The MongoDB Server service was stopped successfully*.
Nếu hiện *service is not started* thì cũng **tốt** — nghĩa là nó vốn đã tắt sẵn.

> Chỉ cần làm **một lần duy nhất** cho mỗi máy. Lần sau mở máy không phải làm lại.

## Bước 3 — Mở cửa sổ lệnh và vào đúng thư mục dự án

**Làm gì:**
1. Mở **File Explorer** (thư mục màu vàng trên thanh dưới màn hình).
2. Vào ổ `C:` → tìm thư mục `NoSQL-NewsCacheSession`.
3. Bấm vào **thanh địa chỉ** ở trên cùng (chỗ ghi đường dẫn), xóa hết, gõ `powershell`
   rồi bấm `Enter`.

**Thấy gì thì đúng:** một cửa sổ nền xanh đậm hiện ra, dòng cuối ghi
`PS C:\NoSQL-NewsCacheSession>`.

> **Gọi cửa sổ này là "Cửa sổ 1".** Đừng đóng nó.

## Bước 4 — Bật MongoDB, Redis và RedisInsight

**Làm gì:** trong Cửa sổ 1, gõ dòng này rồi `Enter`:

```powershell
docker compose up -d
```

**Thấy gì thì đúng:** ba dòng chữ, mỗi dòng có chữ `Started` hoặc `Running`:

```
Container news-mongo         Started
Container news-redis         Started
Container news-redisinsight  Started
```

**Kiểm tra lại cho chắc:**

```powershell
docker compose ps
```

Phải thấy đủ **ba dòng**, cột `STATUS` đều ghi `Up`.

## Bước 5 — Bật chương trình chính (API)

**Làm gì:** vẫn trong Cửa sổ 1, gõ:

```powershell
dotnet run --project src/NewsCacheSession.Api --urls http://localhost:5134
```

**Chờ khoảng 10–30 giây.**

**Thấy gì thì đúng:** dòng chữ
`Now listening on: http://localhost:5134`.

> ⚠️ **Cửa sổ 1 từ giờ bị "khóa"** — nó đang chạy chương trình, không gõ lệnh khác vào
> được nữa. **Đừng đóng, đừng bấm Ctrl+C.** Thu nhỏ nó xuống.

## Bước 6 — Kiểm tra sức khỏe hệ thống

**Làm gì:**
1. Mở **cửa sổ lệnh thứ hai**: làm lại đúng **Bước 3**.
2. Gõ:

```powershell
curl http://localhost:5134/health
```

**Thấy gì thì đúng:** một đoạn chữ có `"status":"Healthy"` **hai lần** — một cho
`mongodb`, một cho `redis`.

> **Gọi cửa sổ này là "Cửa sổ 2".** Đây là cửa sổ để gõ các lệnh về sau.

❌ Nếu thấy chữ `Unhealthy` hoặc báo lỗi → quay lại **Bước 4**, xem Docker đã lên chưa.

## Bước 7 — Nạp dữ liệu (chỉ làm khi kho đang rỗng)

**Kiểm tra trước đã.** Trong Cửa sổ 2, gõ:

```powershell
curl "http://localhost:5134/api/posts?pageSize=1"
```

- Thấy có chữ `"totalItems":` kèm số **lớn hơn 100** → **đã có dữ liệu, bỏ qua bước này**.
- Thấy `"totalItems":0` → làm tiếp bên dưới.

**Làm gì (lần đầu dùng máy thì chạy cả 2 dòng, lần sau chỉ chạy dòng dưới):**

```powershell
python -m pip install -r scripts/SeedPosts/requirements.txt
python scripts/SeedPosts/seed.py
```

**Thấy gì thì đúng:** `Đã seed 100 bài mẫu có ảnh vào newsdb.posts`.

**Tạo tài khoản quản trị** (chỉ khi chưa có): mở trình duyệt vào
`http://localhost:5134/swagger` → tìm dòng `POST /api/auth/register` → bấm **Try it out**
→ sửa phần chữ trong khung thành:

```json
{ "username": "admin", "password": "Matkhau123" }
```

→ bấm nút xanh **Execute**.

> ⭐ **Người đăng ký đầu tiên tự động làm quản trị viên.** Không có tài khoản admin cài
> sẵn, nên tài khoản này phải được tạo trước tiên.

## Bước 8 — Bật giao diện web

**Làm gì:**
1. Mở **cửa sổ lệnh thứ ba** (làm lại Bước 3). Gọi là **Cửa sổ 3**.
2. Gõ từng dòng:

```powershell
cd src\frontend
npm install
npm run dev
```

> `npm install` chỉ cần chạy **lần đầu tiên trên máy đó**. Lần sau bỏ qua, chạy thẳng
> `npm run dev`.

**Thấy gì thì đúng:** dòng chữ `Local: http://localhost:3000/`.

**Mở trình duyệt, gõ địa chỉ:** `http://localhost:3000`
→ phải thấy trang tin tức có chữ **NEWSCACHE** ở giữa trên cùng và danh sách bài viết.

## Bước 9 — Mở RedisInsight để nhìn vào bên trong Redis

**Làm gì:**
1. Mở một tab trình duyệt mới, gõ: `http://localhost:5540`
2. Lần đầu nó hỏi kết nối → chọn **Add Redis database** →
   **Host** gõ `host.docker.internal`, **Port** gõ `6379` → bấm **Add Redis Database**.
3. Bấm vào tên cơ sở dữ liệu vừa thêm → bấm mục **Browser** ở cột bên trái.

**Thấy gì thì đúng:** một danh sách các dòng chữ như `session:...`, `post:...`,
`posts:ver`.

---

## ✅ Bảng kiểm trước khi demo

| | Phải thấy |
|---|---|
| Docker Desktop | Con cá voi **xanh lá**, chữ *Engine running* |
| Cửa sổ 1 | `Now listening on: http://localhost:5134` |
| Cửa sổ 3 | `Local: http://localhost:3000/` |
| Trình duyệt tab 1 | `http://localhost:3000` — thấy trang NEWSCACHE có bài viết |
| Trình duyệt tab 2 | `http://localhost:5540` — RedisInsight thấy danh sách key |

**Tổng thời gian chuẩn bị: khoảng 5 phút** (lần đầu lâu hơn vì phải `npm install`).

---

# PHẦN B — Cách đo hiệu năng

## B1. Vì sao phải đo

Nhóm nói "có cache thì nhanh hơn". Thầy sẽ hỏi: **nhanh hơn bao nhiêu?** Phải có con số,
và con số phải **đo thật**.

## B2. Đo ba thứ, không phải hai

| Tên gọi | Đường dẫn | Ý nghĩa |
|---|---|---|
| **Không cache** | `/api/posts/slug/{slug}` | Đường đọc thẳng MongoDB, **cố ý không cache**, dùng làm mốc "trước khi có cache" |
| **Cache MISS** | `/api/posts/{id}` sau khi xóa key | Lần đọc đầu: tìm trong Redis không thấy → đọc MongoDB → **ghi lại vào Redis** |
| **Cache HIT** | `/api/posts/{id}` gọi ngay lần nữa | Lần đọc sau: lấy thẳng từ Redis |

## B3. Chạy đo

**Làm gì:**
1. Mở **Notepad**.
2. Chép **toàn bộ** đoạn chữ dưới đây vào.
3. Bấm `Ctrl + S`. Ở ô *Save as type* chọn **All Files**. Đặt tên là
   `do-hieu-nang.ps1`. Lưu vào thư mục `C:\NoSQL-NewsCacheSession`.

```powershell
# do-hieu-nang.ps1 — Đo thời gian đọc bài viết: MongoDB vs Redis
$SoLan  = 20
$Api    = "http://localhost:5134/api"
$KetQua = "ket-qua-do.csv"

Write-Host "Dang lay mot bai viet de do..." -ForegroundColor Cyan
$bai  = (Invoke-RestMethod "$Api/posts?page=1&pageSize=1").items[0]
$id   = $bai.id
$slug = $bai.slug
Write-Host "  Bai: $($bai.title)"
Write-Host ""

function Do-Mot-Lan($url) {
    $ms = (curl.exe -s -o NUL -w "%{time_total}" $url)
    return [math]::Round([double]$ms * 1000, 2)
}

$rows = @()
Write-Host "Dang do $SoLan luot..." -ForegroundColor Cyan
for ($i = 1; $i -le $SoLan; $i++) {
    $t1 = Do-Mot-Lan "$Api/posts/slug/$slug"
    docker exec news-redis redis-cli DEL "post:$id" | Out-Null
    $t2 = Do-Mot-Lan "$Api/posts/$id"
    $t3 = Do-Mot-Lan "$Api/posts/$id"
    $rows += [pscustomobject]@{ lan = $i; loai = "1-KhongCache-MongoDB"; ms = $t1 }
    $rows += [pscustomobject]@{ lan = $i; loai = "2-CacheMISS-MongoDB";  ms = $t2 }
    $rows += [pscustomobject]@{ lan = $i; loai = "3-CacheHIT-Redis";     ms = $t3 }
    Write-Host ("  luot {0,2}: khong-cache {1,6} ms | MISS {2,6} ms | HIT {3,6} ms" -f $i, $t1, $t2, $t3)
}

$rows | Export-Csv -Path $KetQua -NoTypeInformation -Encoding utf8

Write-Host ""
Write-Host "=== KET QUA TRUNG BINH ===" -ForegroundColor Green
$tomTat = $rows | Group-Object loai | ForEach-Object {
    $v = $_.Group.ms
    [pscustomobject]@{
        Loai      = $_.Name
        TrungBinh = [math]::Round(($v | Measure-Object -Average).Average, 2)
        NhanhNhat = ($v | Measure-Object -Minimum).Minimum
        ChamNhat  = ($v | Measure-Object -Maximum).Maximum
    }
}
$tomTat | Format-Table -AutoSize
$tbMiss = ($tomTat | Where-Object Loai -eq "2-CacheMISS-MongoDB").TrungBinh
$tbHit  = ($tomTat | Where-Object Loai -eq "3-CacheHIT-Redis").TrungBinh
Write-Host ("Redis nhanh hon MongoDB: {0} lan" -f [math]::Round($tbMiss / $tbHit, 2)) -ForegroundColor Yellow
Write-Host "Da luu file: $KetQua" -ForegroundColor Green
```

4. Quay lại **Cửa sổ 2**, gõ:

```powershell
.\do-hieu-nang.ps1
```

❌ Nếu báo lỗi *không thể chạy script*, gõ dòng này một lần rồi chạy lại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Mất khoảng 1 phút.** Xong sẽ có file `ket-qua-do.csv` trong thư mục dự án.

## B4. Kết quả thật đo được ngày 23/10/2026

Đây là **kết quả thật** chạy trên máy SV1, cơ sở dữ liệu có 101 bài, 20 lượt mỗi loại:

| Loại | Trung bình | Nhanh nhất | Chậm nhất |
|---|---|---|---|
| 1 — Không cache (MongoDB) | **5,95 ms** | 3,56 ms | 10,79 ms |
| 2 — Cache MISS (MongoDB) | **14,15 ms** | 7,99 ms | 40,24 ms |
| 3 — Cache HIT (Redis) | **4,61 ms** | 2,72 ms | 10,16 ms |

→ **Cache HIT nhanh hơn Cache MISS 3,07 lần.**

## B5. ⚠️ Ba điều phải hiểu trước khi đem số này đi báo cáo

**Điều 1 — Vì sao "Cache MISS" lại CHẬM HƠN "Không cache"?**

Nhìn bảng thấy lạ: 14,15 ms chậm hơn 5,95 ms. Không phải máy hỏng. Lý do: lần MISS phải
làm **nhiều việc hơn**:

1. Tìm trong Redis (không thấy)
2. Giành khóa chống dồn
3. Tìm lại trong Redis lần nữa cho chắc
4. Đọc MongoDB
5. Đóng gói thành chữ JSON
6. **Ghi ngược vào Redis**
7. Nhả khóa

Còn "không cache" thì chỉ đọc MongoDB rồi trả về. **Đây là điều hoàn toàn bình thường của
mẫu Cache-Aside: lần đọc đầu tiên phải trả thêm chi phí để đổi lấy những lần sau nhanh.**
Nếu thầy hỏi, trả lời đúng như vậy.

**Điều 2 — Vì sao không đạt "200ms so với 5ms" như đề bài mô tả?**

Vì ba lý do, nói thẳng được:

1. MongoDB đang chạy **ngay trên cùng một máy**, không phải qua mạng.
2. Dữ liệu mới có 101 bài — còn **quá nhỏ**, MongoDB giữ sẵn trong bộ nhớ.
3. Bài viết đã có **chỉ mục** nên tìm rất nhanh.
4. Khoảng 3–4 ms trong mỗi con số là **chi phí truyền qua HTTP**, không phải thời gian đọc
   dữ liệu. Đây là mức sàn không thể giảm.

**Tuyệt đối không sửa số cho đẹp.** Báo cáo đúng số đo được, kèm giải thích, là cách ăn
điểm. Sửa số mà bị hỏi sâu là mất nhiều hơn.

**Điều 3 — Muốn khoảng cách rõ hơn một cách trung thực thì làm gì?**

Nạp nhiều dữ liệu hơn rồi đo lại:

```powershell
python scripts/SeedPosts/seed.py --count 1000
```

Rồi chạy lại `.\do-hieu-nang.ps1`. Dữ liệu càng lớn, MongoDB càng phải làm việc nhiều, chênh
lệch càng rõ. **Đây là cách làm số đẹp lên mà vẫn trung thực.**

> 🚫 **Đừng mất công thử cách này:** bắn nhiều request cùng lúc bằng cách mở nhiều tiến
> trình `curl` trên Windows. Nhóm đã thử: thời gian đo ra bị **chi phí khởi tạo tiến trình
> của Windows nuốt mất**, ba phép đo khác nhau đều ra xấp xỉ 3,4–4,0 giây, không nói lên
> điều gì.

## B6. Vẽ biểu đồ từ file kết quả

**Làm gì:**
1. Mở thư mục `C:\NoSQL-NewsCacheSession`, bấm đúp vào file **`ket-qua-do.csv`** → mở bằng
   **Excel**.
2. Ở ô trống bên phải, gõ ba dòng nhãn và dùng hàm tính trung bình cho từng loại:

| | A | B |
|---|---|---|
| 1 | Không cache (MongoDB) | `=AVERAGEIF(B:B,"1-KhongCache-MongoDB",C:C)` |
| 2 | Cache MISS (MongoDB) | `=AVERAGEIF(B:B,"2-CacheMISS-MongoDB",C:C)` |
| 3 | Cache HIT (Redis) | `=AVERAGEIF(B:B,"3-CacheHIT-Redis",C:C)` |

3. Bôi đen cả 3 dòng vừa làm → thẻ **Insert** → chọn **Biểu đồ cột** (Column Chart).
4. Bấm chuột phải vào biểu đồ → **Add Data Labels** để hiện số trên đầu mỗi cột.
5. Đặt tiêu đề biểu đồ: **"Thời gian đọc một bài viết (mili giây, trung bình 20 lượt)"**.
6. Bấm chuột phải vào biểu đồ → **Save as Picture** → lưu thành `bieu-do-hieu-nang.png`.

**Dưới biểu đồ nhớ ghi một dòng chú thích:**

> *Đo ngày __/__/2026, 20 lượt mỗi loại, cơ sở dữ liệu 101 bài viết, chạy trên một máy
> tính cá nhân.*

---

# PHẦN C — Kịch bản demo trước thầy

**Trước khi bắt đầu:** làm xong **toàn bộ Phần A**, và mở sẵn **2 tab trình duyệt**:
tab 1 là `http://localhost:3000`, tab 2 là `http://localhost:5540` (RedisInsight).

---

## 🎬 Bước 1 — Lần đầu chậm, lần sau nhanh *(người làm: Định)*

**Nói:** *"Em sẽ mở một bài viết chưa từng được đọc. Lần đầu hệ thống phải vào MongoDB
lấy. Lần thứ hai nó lấy từ Redis."*

**Làm từng cú một:**

1. Sang **tab 1** (`localhost:3000`).
2. Bấm phím **`F12`** → một bảng hiện ra bên phải → bấm vào thẻ **Network**.
3. Bấm phím **`Ctrl + R`** để tải lại trang.
4. **Bấm vào tiêu đề một bài viết bất kỳ** trong danh sách.
5. **Chỉ tay lên màn hình** vào huy hiệu ở gần đầu bài viết → nó ghi **`MISS`**.
6. **Bấm `Ctrl + R`** để tải lại đúng bài đó.
7. Huy hiệu bây giờ đổi thành **`HIT`**, và con số mili giây bên cạnh **nhỏ hơn**.

**Chốt một câu:** *"MISS là lấy từ MongoDB, HIT là lấy từ Redis. Lần thứ hai nhanh hơn."*

---

## 🎬 Bước 2 — Sửa bài thì bộ nhớ đệm bị xóa ngay *(người làm: Như sửa, Quân chỉ Redis)*

Đây là bước **quan trọng nhất**, chứng minh dữ liệu không bao giờ cũ.

**Chuẩn bị:** đang ở trang chi tiết bài viết. **Nhìn lên thanh địa chỉ**, phần đuôi có dạng
`/posts/6adacc...` — **đó là mã số bài viết**, nhớ vài ký tự đầu.

**Làm từng cú một:**

1. **Quân** sang **tab 2** (RedisInsight) → bấm **Browser** → trong ô tìm kiếm gõ:
   `post:*` → bấm `Enter`.
2. **Chỉ tay** vào dòng `post:<mã số bài>` → *"Đây là bản ghi nhớ của bài viết, đang nằm
   trong Redis."*
3. Bấm vào dòng đó → bên phải hiện chữ **TTL** kèm một con số đang **giảm dần** →
   *"Nó tự hết hạn sau 10 phút."*
4. **Như** sang **tab 1** → bấm nút **Sửa** → đổi tiêu đề hoặc nội dung → bấm **Lưu**.
5. **Quân** quay lại **tab 2** → bấm nút **làm mới** (hình mũi tên tròn) ở danh sách key.
6. **Chỉ tay:** dòng `post:<mã số bài>` **đã biến mất**.
7. **Định** sang tab 1 → bấm `Ctrl + R` → huy hiệu hiện **`MISS`**, và nội dung là **bản
   vừa sửa**.
8. Bấm `Ctrl + R` lần nữa → quay lại **`HIT`**.

**Chốt một câu:** *"Hệ thống ghi vào MongoDB trước, xóa Redis sau. Nhờ vậy không ai đọc
phải bản cũ."*

---

## 🎬 Bước 3 — Phiên đăng nhập tự đếm ngược *(người làm: Định)*

**Làm từng cú một:**

1. Sang **tab 1** → bấm **Đăng nhập** → gõ `admin` / `Matkhau123` → bấm **Đăng nhập**.
2. Sang **tab 2** (RedisInsight) → ô tìm kiếm gõ `session:*` → `Enter`.
3. Bấm vào một dòng `session:...`.
4. **Chỉ tay vào hai chỗ:**
   - Bên phải có các dòng `userId`, `username`, `role`, `loginAt` →
     *"Đây là cấu trúc Hash mà đề bài yêu cầu — một phiên gồm nhiều mẩu thông tin."*
   - Chữ **TTL** kèm con số đang **giảm dần từ 1800 giây** →
     *"Phiên tự hết hạn sau 30 phút."*
5. Bấm nút **làm mới** vài lần → con số TTL **giảm dần**.
6. Sang tab 1, **bấm vào một bài viết bất kỳ** (tức là còn hoạt động).
7. Quay lại tab 2, bấm **làm mới** → **TTL nhảy trở lại gần 1800**.

**Chốt một câu:** *"Còn hoạt động thì phiên được gia hạn; bỏ máy 30 phút thì tự đăng
xuất."*

---

## 🎬 Bước 4 — Số liệu đo *(người làm: Định)*

1. Chiếu **biểu đồ cột** đã vẽ ở phần B6.
2. Nói đúng ba ý:
   - *"Nhóm đo 20 lượt mỗi loại, trên một máy cá nhân, cơ sở dữ liệu 101 bài."*
   - *"HIT nhanh hơn MISS khoảng 3 lần."*
   - *"Nhóm chưa đạt mức chênh lệch lớn như mô tả trong đề, vì MongoDB chạy ngay trên máy,
     dữ liệu còn nhỏ và đã có chỉ mục. Nhóm xin báo cáo đúng số đo được."*

> Chủ động nói ra điểm yếu **trước khi bị hỏi** là cách giữ điểm tốt nhất.

---

## 🎬 Bước 5 — Nếu còn thời gian: định mức dữ liệu

Trong **Cửa sổ 2**, gõ hai lệnh, chiếu kết quả lên:

```powershell
docker exec news-mongo mongosh --quiet --eval "db.getSiblingDB('newsdb').posts.countDocuments({})"
docker exec news-redis redis-cli DBSIZE
```

**Nói:** *"Đề bài yêu cầu tối thiểu 100 bài viết và 20–50 key Redis có thời hạn khác nhau.
Nhóm em đạt đủ."*

---

# PHẦN D — Khi có sự cố

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Trang `localhost:3000` trắng trơn, không có bài nào | Chưa nạp dữ liệu | Làm **Bước 7** Phần A |
| `curl ... /health` báo `Unhealthy` | Docker chưa lên hẳn | Chờ thêm 1 phút, chạy lại `docker compose up -d` |
| Huy hiệu luôn hiện `MISS`, không bao giờ `HIT` | Redis chưa chạy | Cửa sổ 2 gõ `docker compose ps`, xem `news-redis` có `Up` không |
| RedisInsight không thấy key nào | Kết nối sai địa chỉ | Sửa Host thành `host.docker.internal`, Port `6379` |
| Mở bài viết báo lỗi 500 | API chưa chạy hoặc đã tắt | Xem **Cửa sổ 1** còn dòng `Now listening on` không |
| Bấm Sửa bài bị báo **403** | Đang đăng nhập bằng tài khoản thường | 100 bài nạp mẫu không có tác giả nên **chỉ quản trị viên sửa được**. Đăng nhập lại bằng `admin`. **Đây là thiết kế có chủ ý, không phải lỗi** |
| `dotnet test` báo lỗi `NETSDK1045` | Máy chỉ có .NET SDK 9, dự án test nhắm .NET 10 | Lỗi cấu hình, **không phải lỗi mã nguồn**. Đừng demo lệnh này nếu chưa xử lý |
| Script `.ps1` không chạy được | Windows chặn script | Gõ `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` rồi chạy lại |

## Cách tắt toàn bộ sau khi demo xong

1. Bấm vào **Cửa sổ 1**, bấm `Ctrl + C` → API dừng.
2. Bấm vào **Cửa sổ 3**, bấm `Ctrl + C` → giao diện dừng.
3. Trong **Cửa sổ 2**, gõ: `docker compose down`

---

# Ghi chú về phân công

File `scripts/Benchmark/benchmark.py` **thuộc phần việc của SV3 (Định)** và hiện vẫn là
khung rỗng. Hướng dẫn ở **Phần B** cố ý **không sửa file đó** — nó dùng một script
PowerShell riêng, chạy độc lập, nên Định vẫn tự viết bản Python của mình bình thường. Hai
bên không đụng nhau.

Nếu Định muốn, có thể dùng thẳng kết quả `ket-qua-do.csv` ở Phần B làm số liệu cho chương
kiểm thử hiệu năng, miễn là ghi rõ phương pháp đo như ở mục B4 và B5.
