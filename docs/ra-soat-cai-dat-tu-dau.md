# Rà soát cài đặt từ đầu (SCRUM-47)

**Chạy ngày 23/10/2026** trên máy SV1 (Windows 11, .NET SDK 9.0.304, Python 3.10.11,
Docker Desktop 28.3.2). Đi đúng theo mục "Cách chạy" của `README.md`, ghi lại **mọi bước
sai**. Kết quả cuối: **toàn hệ thống chạy được**, nhưng README **không đủ để cài từ máy
sạch** — thiếu 5 bước và có 1 lỗi chắc chắn vấp.

---

## 1. Sửa xung đột cổng 27017

**Triệu chứng:** máy có **cả service MongoDB native của Windows lẫn container
`news-mongo`**, cả hai cùng nhắm cổng 27017. Service native thắng (nghe
`127.0.0.1:27017`, `StartType=Automatic`), nên API nối vào bản native còn Docker volume
không được dùng — `mongosh` trong container soi ra DB rỗng.

**Cách sửa đã dùng** (chạy trong PowerShell **có quyền admin**):

```powershell
net stop MongoDB
Set-Service MongoDB -StartupType Manual
```

Chuyển sang `Manual` để service **không tự bật lại sau khi khởi động lại máy**.

**Đã cân nhắc và loại bỏ:** đổi cổng trong `docker-compose.yml` / `appsettings.json` —
hai file dùng chung, sửa là đẩy vấn đề sang máy Quân và Định.

**Hệ quả quan trọng đã xác nhận:** sau khi đổi, container Mongo chỉ có **0 bài viết,
0 user, 2 chuyên mục**. Toàn bộ dữ liệu làm việc trước đây nằm ở **Mongo native**, không
nằm trong Docker volume. **Phải seed lại** (mục 3 bên dưới).

**Kiểm chứng:**

```
Service MongoDB: Status=Stopped StartType=Manual
news-mongo  Up  0.0.0.0:27017->27017/tcp      ← container nay giữ cổng
```

---

## 2. Mười chỗ README thiếu hoặc sai

| # | Vấn đề | Mức | Bằng chứng từ lần chạy này |
|---|---|---|---|
| 1 | **Thiếu `npm install`** trước `npm run dev` | 🔴 Chặn | `src/frontend/node_modules` **không tồn tại**; phải cài mới chạy được |
| 2 | **Ba lệnh `cd` nối tiếp trong cùng shell.** Bước 2 `cd src/NewsCacheSession.Api`, bước 3 lại `cd src/frontend` (đường dẫn **tương đối**) → đang đứng trong thư mục API thì không có `src/frontend` | 🔴 Chặn | Ai làm đúng theo README cũng vấp |
| 3 | **Không có bước seed dữ liệu nào** trong mục "Cách chạy" | 🔴 Chặn | DB sạch có **0 bài** → trang chủ trắng, không demo được |
| 4 | **Thiếu `pip install -r`** cho script seed | 🔴 Chặn | `pymongo`, `faker`, `redis` đều **chưa cài** |
| 5 | **Thiếu bước tạo tài khoản `role=user`** mà `seed_redis.py` bắt buộc phải có | 🟠 Chặn seed Redis | Phải đăng ký `demo_user` thì script mới chạy |
| 6 | **Không có mục yêu cầu cài đặt** (.NET 8 SDK, Node.js, Docker Desktop, Python 3.10+) | 🟠 | — |
| 7 | **Không cảnh báo xung đột cổng 27017** với MongoDB native | 🟠 | Chính vấn đề ở mục 1, mất nhiều thời gian nhất |
| 8 | **Không nói tài khoản đăng ký đầu tiên tự thành admin** | 🟠 | Người cài mới không biết cách có quyền admin |
| 9 | **Thiếu lệnh test** và cảnh báo lệch SDK | 🟡 | `dotnet test` **fail chắc chắn** trên SDK 9 (xem mục 5) |
| 10 | Mục "Tài liệu" thiếu `bao-cao-nguyen-ly-cache-aside.md`, `checklist-barem.md`, file này | 🟡 | — |

Thêm: README ghi **"Nguyễn Anh Quan"** trong khi tên tác giả trên git là
**"Nguyễn Anh Quân"**. ✅ Đã chốt tên đúng là **Quân** và sửa trong `README.md`,
`AGENTS.md`, `src/NewsCacheSession.Api/CLAUDE.md`, `docs/chot-thiet-ke-sv1.md`.

✅ **Đã sửa `README.md`** theo cả 10 điểm trên (có sự đồng ý của nhóm, vì là file dùng
chung). Hai chỗ vẫn còn ghi "Quan" nhưng **không sửa vì là file của người khác**:
`docs/bao-cao-nguyen-ly-cache-aside.md` (Quân tự ghi tên mình) và
`plans/2026-10-04-.../plan.md`. `docs/nosql-jira-tasks.csv` giữ "Quan" vì toàn file dùng
chữ không dấu.

---

## 3. Trình tự đúng, đã chạy thông từ đầu đến cuối

```bash
# 0. Dừng MongoDB native nếu máy có (PowerShell admin) — xem mục 1
net stop MongoDB ; Set-Service MongoDB -StartupType Manual

# 1. Hạ tầng
docker compose up -d                       # mongo 27017, redis 6379, redisinsight 5540

# 2. Backend (chạy từ GỐC repo, không cd)
dotnet run --project src/NewsCacheSession.Api --urls http://localhost:5134

# 3. Kiểm tra sức khỏe trước khi đi tiếp
curl http://localhost:5134/health          # phải thấy "status":"Healthy" cả mongodb lẫn redis

# 4. Seed 100 bài viết
python -m pip install -r scripts/SeedPosts/requirements.txt
python scripts/SeedPosts/seed.py --dry-run
python scripts/SeedPosts/seed.py

# 5. Tạo tài khoản — NGƯỜI ĐĂNG KÝ ĐẦU TIÊN TỰ THÀNH ADMIN
#    rồi tạo thêm một tài khoản thường cho seed Redis
#    (qua Swagger /swagger hoặc POST /api/auth/register)

# 6. Seed 20-50 session/cache key TTL khác nhau
python -m pip install -r scripts/SeedRedis/requirements.txt
python scripts/SeedRedis/seed_redis.py --demo-username demo_user --dry-run
python scripts/SeedRedis/seed_redis.py --demo-username demo_user

# 7. Frontend (shell RIÊNG, từ gốc repo)
cd src/frontend && npm install && npm run dev
```

---

## 4. Kết quả kiểm chứng — toàn bộ PASS

### Hạ tầng

```
/health  ->  {"status":"Healthy", mongodb: Healthy, redis: Healthy (latency 2,17ms)}
frontend http://localhost:3000  ->  HTTP 200
proxy /api qua frontend         ->  HTTP 200
```

### Xác thực (phần SV1)

| Ca kiểm thử | Kết quả |
|---|---|
| Đăng ký user đầu tiên | ✅ `201`, `"role":"admin"` — bootstrap admin hoạt động |
| Đăng nhập | ✅ `200`, trả `sessionId` + `role` |
| Sai mật khẩu | ✅ `401` `"Sai username hoặc password"` |
| Sai username | ✅ `401` **cùng một thông báo** — không lộ username nào có thật |
| Đăng ký user thứ hai | ✅ `201`, `"role":"user"` — chỉ người đầu tiên là admin |

### CRUD và slug (phần SV1)

| Ca kiểm thử | Kết quả |
|---|---|
| Tạo chuyên mục trùng slug | ✅ `409` `"Chuyên mục với slug \"thoi-su\" đã tồn tại."` |
| Sinh slug tiếng Việt có chữ **Đ** | ✅ `Đội tuyển Việt Nam thắng đậm` → `doi-tuyen-viet-nam-thang-dam` |
| Sửa bài | ✅ `200`, nội dung mới đọc ra đúng |

### Hợp đồng dữ liệu — soi thẳng MongoDB

```
posts: 101        categories: 5
fields: _id,title,slug,content,imageUrl,categoryId,authorId,views,isDeleted,deletedAt,createdAt,updatedAt
categoryId là ObjectId: 100      categoryId là string: 0      ← camelCase + ObjectId đúng hợp đồng
authorId  là ObjectId:   1       authorId null (bài seed): 100 ← bài seed chỉ admin sửa được, đúng thiết kế
createdAt: kiểu Date
index posts:      ux_posts_slug, ix_posts_category_createdAt, ix_posts_createdAt
index users:      ux_users_username
index categories: ux_categories_slug
```

Cả 5 index đều được `MongoIndexInitializer` tạo tự động lúc khởi động.

### Cache-Aside và Invalidation — **bước 2 kịch bản demo**

| Bước | Kết quả |
|---|---|
| GET `/api/posts/{id}` lần 1 | ✅ `X-Cache: MISS` |
| GET lần 2, lần 3 | ✅ `X-Cache: HIT` |
| Key `post:{id}` trong Redis | ✅ tồn tại, `TTL = 599` giây (đúng 10 phút) |
| **Sửa bài** → `EXISTS post:{id}` | ✅ **`0`** — cache cũ biến mất ngay |
| GET lại sau khi sửa | ✅ `X-Cache: MISS`, trả **nội dung mới** |

### Bộ đếm lượt xem và cache danh sách

```
3 lần POST /api/posts/{id}/view  ->  post:{id}:views = 3
TTL post:{id}:views = -1                     ← không hết hạn, đúng thiết kế
GET /api/posts  lần 1 MISS, lần 2 HIT
posts:ver = 14        key sinh ra: posts:cat:all:p1:v14    ← versioning hoạt động đúng
```

### Định mức dữ liệu mẫu của đề bài

| Yêu cầu | Thực tế | Đạt |
|---|---|---|
| MongoDB ≥ 100 bài viết có ảnh | **101 bài** (100 seed + 1 test) | ✅ |
| Redis 20–50 session/cache key **TTL khác nhau** | **41 key**: 21 `session:*` (kiểu Hash) + 20 cache | ✅ |
| TTL khác nhau | 454s · 768s · 1083s · 1321s · 1480s … | ✅ |

---

## 5. Bộ test

| Bộ | Kết quả |
|---|---|
| Frontend `npm test` (Vitest) | ✅ **11 file, 101 test, PASS hết**, 7.12s |
| Backend `dotnet test` | ❌ **FAIL lúc build** |

```
error NETSDK1045: The current .NET SDK does not support targeting .NET 10.0.
[C:\NoSQL-NewsCacheSession\tests\NewsCacheSession.Tests\NewsCacheSession.Tests.csproj]
```

**Đây là lệch TargetFramework, không phải lỗi code**: project test nhắm `net10.0`, máy có
SDK 9.0.304. Build riêng API vẫn sạch — `Build succeeded, 0 Warning, 0 Error`.

🔴 **Phải chốt trước demo:** cài .NET SDK 10, hoặc hạ `TargetFramework` của project test
xuống `net8.0`. Nếu thầy yêu cầu chạy test tại chỗ mà máy demo không có SDK 10 thì **mất
luôn phần bằng chứng kiểm thử của SV2**.

---

## 6. ⚠️ Cảnh báo cho kịch bản demo — số đo thật không giống kỳ vọng đề bài

Đo trên máy này, 15 lượt mỗi loại, DB có 101 bài:

| Phép đo | MISS (MongoDB) | HIT (Redis) | Chênh |
|---|---|---|---|
| Chi tiết bài `/api/posts/{id}` | 11.0 ms | 4.4 ms | **2.5 lần** |
| Danh sách 20 bài `/api/posts` | 20.0 ms | 8.0 ms | **2.5 lần** |

**Đề bài mô tả demo là "lần 1 ~200ms vs lần 2 <5ms" — thực tế nhóm đo được chỉ chênh 2.5
lần, không phải 40 lần.** Lý do: MongoDB chạy local, dữ liệu nhỏ, lại có sẵn index nên
đọc rất nhanh; phần lớn 4.4 ms của HIT là chi phí HTTP chứ không phải Redis.

**Cách xử lý trung thực (quy tắc "số đo phải trung thực"):**

- **Không** chỉnh số cho đẹp.
- Nói thẳng khi báo cáo: chênh lệch thật là ~2.5 lần ở quy mô dữ liệu đồ án, và **giải
  thích vì sao** — cache thắng rõ rệt khi dữ liệu lớn hơn bộ nhớ đệm của MongoDB, khi có
  nhiều truy vấn đồng thời, hoặc khi một lần đọc cần `$lookup` nhiều collection.
- Muốn con số đẹp hơn một cách **trung thực**: tăng số bài lên 1.000+ (`seed.py --count
  1000`), hoặc đo dưới tải đồng thời thay vì một request lẻ. Đây là việc của SV3
  (SCRUM-40) và là lý do phần benchmark **không nên bỏ**.

---

## 7. Việc còn phải làm sau lần rà soát này

- [x] ~~Sửa `README.md` theo 10 điểm ở mục 2~~ — **xong 23/10**
- [x] ~~Chốt tên "Quan" hay "Quân"~~ — **Quân**, đã sửa trong các file của SV1
- [ ] Chốt xử lý lệch `net10.0` / `net8.0` của project test — **cần hỏi Quân**
- [ ] SV3 chạy benchmark ở quy mô lớn hơn để có số đo thuyết phục (SCRUM-40/41/42)
- [ ] Trước demo: `db.posts.drop()` + `db.users.drop()` rồi seed lại sạch, vì DB hiện có
      lẫn 1 bài và 2 tài khoản tạo ra khi smoke test (`admin`, `demo_user`)
