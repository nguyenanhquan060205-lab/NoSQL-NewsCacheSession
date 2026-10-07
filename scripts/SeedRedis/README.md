# SCRUM-36 — seed session và cache Redis

Mặc định **40 key = 20 session Hash + 20 cache bài viết thật**.
`--total 50` chia 25 + 25. Đây là số key của run, không phải tổng key toàn Redis.
Session có TTL phân bố 300–1800 giây; cache do API tạo với TTL 600 giây.
TTL khác nhau không có nghĩa mỗi cache phải có TTL riêng.

## Điều kiện chạy

- Docker MongoDB/Redis, API `http://localhost:5134` đang chạy (`/health` trả 200).
- Mongo `newsdb`, Redis DB 0, cùng môi trường local với API. Script chỉ hỗ trợ
  cấu hình loopback này, không dùng ở production hoặc chuyển database tùy ý.
- Username của **tài khoản thường có thật (`role=user`)**, truyền rõ bằng
  `--demo-username`. Không đọc mật khẩu, không tạo user giả hay copy quyền admin.
  Nếu chỉ có admin: đăng ký tài khoản thường qua web/API trước khi seed.
- Có ít nhất 20/25 bài active chưa cache trong tối đa 200 bài mới nhất.
- Tổng phiên đang có + phiên mới không vượt giới hạn 200 của API admin.
- Để kiểm tra admin/revoke: người dùng cung cấp credential admin qua biến môi
  trường tạm `SCRUM36_ADMIN_SESSION`. Không hardcode vào script, Git hay Obsidian.

## Cài đặt (chạy từ thư mục gốc repo)

```powershell
python -m venv scripts/SeedRedis/.venv
scripts/SeedRedis/.venv/Scripts/python.exe -m pip install -r scripts/SeedRedis/requirements.txt
```

Không cần PYTHONPATH hoặc thư mục dependency trong Windows/Temp.

## Seed và resume

Thay `ten-user-demo` bằng username tài khoản thường của bạn:

```powershell
scripts/SeedRedis/.venv/Scripts/python.exe scripts/SeedRedis/seed_redis.py --demo-username ten-user-demo --dry-run
scripts/SeedRedis/.venv/Scripts/python.exe scripts/SeedRedis/seed_redis.py --demo-username ten-user-demo
# Tùy chọn 50 key; đây là run mới, không tự xóa run trước:
scripts/SeedRedis/.venv/Scripts/python.exe scripts/SeedRedis/seed_redis.py --demo-username ten-user-demo --total 50
```

Dry-run chỉ đọc Mongo/Redis, `/health` và endpoint slug **không cache** để xác
nhận API/DB cùng dữ liệu; không tạo token, manifest hay gọi GET by-id.
Seed ghi manifest trong `scripts/SeedRedis/data/<run-id>.json` trước mỗi mutation.
Lấy đúng đường dẫn `manifest` từ JSON kết quả:

```powershell
scripts/SeedRedis/.venv/Scripts/python.exe scripts/SeedRedis/seed_redis.py --demo-username ten-user-demo --resume scripts/SeedRedis/data/<run-id>.json
```

Run 50 cần thêm `--total 50` khi resume. Account/API origin phải khớp manifest.
Resume giữ phiên/cache còn hợp lệ, không reset TTL; phiên mất/hết hạn/thu hồi
được thay bằng **token mới**, token cũ không được hồi sinh. Cache intent đã ghi
trước API: timeout/crash tiếp tục kiểm tra đúng bài đã chọn, không tạo cache dư.
Một run chỉ có một writer; file `.lock` ngăn chạy song song. Nếu process bị kill
để lại lock: xác nhận process cũ đã dừng trước khi gỡ **đúng lock của run đó**.

Exit 0 chỉ khi snapshot có đủ 20/20 hoặc 25/25 key đúng hợp đồng. Exit 1 khi thiếu,
wrong-type, sai DTO/TTL/account hay service lỗi; báo partial và dùng manifest resume.
Nếu tất cả 200 bài đã cache, đợi TTL hết hoặc thử sau; không xóa cache thật để seed.

## Xác minh và demo

Mặc định chỉ đọc Redis/Mongo, không gọi API hoặc gia hạn phiên:

```powershell
scripts/SeedRedis/.venv/Scripts/python.exe scripts/SeedRedis/verify_seed_redis.py scripts/SeedRedis/data/<run-id>.json
# Opt-in: gọi API để chứng minh HIT, sliding TTL và quyền user/admin:
scripts/SeedRedis/.venv/Scripts/python.exe scripts/SeedRedis/verify_seed_redis.py scripts/SeedRedis/data/<run-id>.json --live-api-demo
# Chỉ khi đã có SCRUM36_ADMIN_SESSION và muốn thu hồi 1 phiên thuộc run:
scripts/SeedRedis/.venv/Scripts/python.exe scripts/SeedRedis/verify_seed_redis.py scripts/SeedRedis/data/<run-id>.json --live-api-demo --revoke-one
```

Live demo không chứa credential khi GET bài. Khi gọi `/me` hoặc admin API,
middleware gia hạn TTL của **phiên được dùng** về 30 phút; TTL các phiên demo còn
lại giảm tự nhiên. Thiếu credential admin => phần admin pending, không giả pass.
Revoke làm run còn thiếu 1 key là expected; explicit resume cấp token khác.

1. RedisInsight `http://localhost:5540`: kết nối Redis, lọc `session:scrum36-demo-*`,
   xem Hash đủ `userId/username/role/loginAt/lastActive` và TTL giảm. Dùng post IDs
   trong manifest để xem đúng 20/25 String cache PascalCase, TTL tối đa 600 giây.
2. Trang `/admin/sessions`: đăng nhập admin, tìm username demo, xem thời điểm/TTL;
   thu hồi một phiên demo. Không thu hồi phiên admin hoặc phiên ngoài run.
3. API `/api/posts/{id}` HIT trả đúng title/content/category/date so với Mongo;
   không dùng endpoint slug để demo Cache-Aside. Session user gọi admin nhận 403,
   session hết hạn/thu hồi gọi `/me` nhận 401.

## Tests

```powershell
scripts/SeedRedis/.venv/Scripts/python.exe -m unittest discover -s scripts/SeedRedis -p 'test_*.py' -v
$env:RUN_REDIS_INTEGRATION = '1'
# Chỉ đặt nếu tài khoản thường đó có thật:
$env:SCRUM36_DEMO_USERNAME = 'ten-user-demo'
scripts/SeedRedis/.venv/Scripts/python.exe -m unittest discover -s scripts/SeedRedis -p test_integration.py -v
Remove-Item Env:RUN_REDIS_INTEGRATION
Remove-Item Env:SCRUM36_DEMO_USERNAME
```

Unit tests không kết nối DB. Live tests dùng key riêng `scrum36-test:<uuid>` để
test Lua/expiry, xóa đúng key test vừa tạo; GET bài thật warm một cache và để TTL
tự hết. Không FLUSHDB hoặc xóa dữ liệu trước test. Thiếu account user thì test
xác thực skip có lý do, không tạo account giả để báo pass.

## An toàn / rollback

Manifest chứa **bearer token thật**, không mở/chia sẻ ảnh chụp nội dung; giữ `data/`
cục bộ, kiểm tra quyền truy cập Windows của máy dùng chung. `data/`, `.venv/`,
`__pycache__/` đã ignore riêng tại thư mục script. Output không in session IDs.
Không commit token/admin credential vào README, log, plan hay journal.
Script không ghi Mongo, không seed fake list/counter/lock, không INCR `posts:ver`,
không ghi đè key có sẵn. API tự quản lý lock tạm khi warm bài.
Không tự cleanup; session/cache hết TTL tự mất. Nếu cần dọn ngay, chỉ thu hồi
session đúng run qua admin UI/API sau khi kiểm tra manifest, không dùng SCAN+DEL.
Không tự xóa cache/counter hay chạy lại bản nháp `--count` cũ.
