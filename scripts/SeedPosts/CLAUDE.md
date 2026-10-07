# Script seed dữ liệu mẫu (SCRUM-32 — SV3 — Nguyễn Xuân Định)

Yêu cầu: **tối thiểu 100 bài viết hoàn chỉnh có tiêu đề, nội dung và hình ảnh**.
Script cho phép seed nhiều hơn 100 bài bằng `--count` và kiểm tra an toàn bằng
`--dry-run`.

## Hợp đồng dữ liệu

- Database mặc định `newsdb`, collections `posts` và `categories`.
- URI/database có thể cấu hình qua `MONGODB_URI` và `MONGODB_DATABASE`.
- Field MongoDB phải theo camelCase: `title`, `slug`, `content`, `imageUrl`,
  `categoryId`, `authorId`, `views`, `isDeleted`, `deletedAt`, `createdAt`,
  `updatedAt`.
- `categoryId` phải là `bson.ObjectId` trỏ tới category thực. `authorId` seed là
  `null` theo thiết kế.
- Mỗi bài có URL ảnh nhiếp ảnh Picsum ổn định theo slug seed.
- Lượt xem ban đầu là `0`. Tiêu đề/nội dung do Faker sinh cho dữ liệu kiểm thử,
  không phải tin báo chí được thu thập từ nguồn thật.
- Slug dùng số thứ tự cố định, không phụ thuộc phiên bản Faker; tăng `--count`
  sẽ thêm các bài còn thiếu.
- Script không xóa collection: tạo category nếu chưa có và upsert bài theo slug ổn
  định; các document đã tồn tại được giữ nguyên.

## Cài đặt, chạy và kiểm thử

Chạy từ thư mục gốc repo:

```powershell
python -m pip install -r scripts/SeedPosts/requirements.txt
python scripts/SeedPosts/seed.py --dry-run
python scripts/SeedPosts/seed.py
python scripts/SeedPosts/seed.py --count 1000
python -m unittest discover -s scripts/SeedPosts -p "test_*.py"
```

`--count` phải từ 100 trở lên. Nếu dữ liệu cũ dùng field PascalCase, cần backup
và xử lý riêng; script không tự xóa dữ liệu để “dọn” collection.

Seed trực tiếp MongoDB trước khi demo API. Nếu danh sách đã được cache trước khi
seed, cache danh sách cũ tự hết hạn sau 3 phút theo hợp đồng Redis. Script không
sửa session hay bộ đếm lượt xem Redis. Ảnh Picsum cần kết nối Internet.

## Nạp 10.000 bài thật có ảnh

```powershell
python scripts/SeedPosts/import_real.py --count 10000 --wikinews-count 100 --hide-samples
python scripts/SeedPosts/verify_real.py --count 10000
python scripts/SeedPosts/categorize_real.py --dry-run
python scripts/SeedPosts/categorize_real.py
```

- 9.900 bài Wikipedia tiếng Việt từ dataset `wikimedia/wikipedia`, bản
  `20231101.vi`: https://huggingface.co/datasets/wikimedia/wikipedia
- 100 tin Wikinews tiếng Anh từ API nguồn gốc: https://en.wikinews.org
- Wikipedia là nội dung bách khoa; Wikinews là tin tức cộng đồng. Không gắn nhãn
  chúng là bài báo của VnExpress/Tuổi Trẻ hay cơ quan báo chí khác.
- Chọn bài có văn bản từ 500 ký tự trở lên và ảnh Wikimedia Commons có tác giả,
  giấy phép mở. Không dùng ảnh Faker/Picsum cho bài thật. Nguồn bài, nguồn ảnh,
  tác giả ảnh và giấy phép được ghi cuối `content`, hiển thị trên web; không thêm
  field vào model/backend của thành viên khác.
- `createdAt` của Wikipedia là ngày snapshot 01/11/2023, không phải ngày xuất bản
  bài báo. Wikinews dùng ngày sửa đổi nguồn, có ghi rõ trong phần nguồn.
- Slug chứa nguồn + page ID. Chạy lại giữ bài đã có và tiếp tục nạp phần thiếu.
  Ghi MongoDB trước, `INCR posts:ver` sau mỗi batch; không xóa session hoặc counter.
- Sau khi import, bài Wikipedia được phân vào 5 chủ đề hiện có bằng quy tắc từ
  tiêu đề và phần mở đầu: Công nghệ, Giải trí, Kinh doanh, Thể thao, Thời sự.
  Đây là phân loại tự động theo từ khóa, có thể cần chỉnh tay khi biên tập.
  Bài thiếu tín hiệu rõ ràng giữ ở Tri thức; Wikinews giữ ở Tin quốc tế.
  Phần ghi nguồn không tham gia phân loại. Có `--dry-run` để rà trước khi cập nhật.
  Script chỉ đổi `categoryId`, giữ nguyên nguồn, ảnh, nội dung và lượt xem;
  sau đó xóa cache chi tiết bị ảnh hưởng và tăng phiên bản danh sách.
- `--hide-samples` ẩn mềm các bài Faker chưa sửa do script cũ tạo, sau khi nạp đủ
  bài thật. Có thể khôi phục bằng cách bỏ `isDeleted`; không xóa vật lý bài.
- Dataset tải về và manifest ghi nguồn nằm trong `scripts/SeedPosts/data/`, được
  bỏ qua bởi Git. Máy cần khoảng 1 GB dung lượng trống và Internet. Ảnh dùng URL
  gốc thumbnail Commons, không upload bản sao; có thể phụ thuộc nguồn bên ngoài.
- `REDIS_URL` mặc định `redis://localhost:6379/0`; MongoDB dùng cấu hình ở trên.

## Bổ sung tin gần đây qua RSS — demo phi lợi nhuận

```powershell
python import_rss.py --dry-run
python import_rss.py --days 14 --per-category 30
```

Lấy tối đa 30 tin/chuyên mục từ RSS chính thức VnExpress: Thời sự, Thể thao,
Khoa học công nghệ, Giải trí, Kinh doanh. Chỉ lưu tiêu đề, tóm tắt, ảnh RSS
và link nguồn; không cào toàn bài, không sửa ngày xuất bản. Bài ghi rõ là
tóm tắt RSS và có nút đọc toàn bài trên VnExpress.

Điều khoản: https://vnexpress.net/rss — dùng cho cá nhân/phi lợi nhuận, ghi
rõ nguồn và phải ngừng phân phối nếu nguồn yêu cầu. Không áp dụng mặc định
cho triển khai thương mại.

Script giữ nguyên bài đã có, lượt xem và nội dung chỉnh sửa; không xóa bài cũ.
MongoDB được ghi trước rồi `INCR posts:ver`. Bộ Wikipedia/Wikinews vẫn có
10.000 bài; tin RSS là phần bổ sung, tổng active có thể lớn hơn 10.000.
Chạy lại script để lấy tin mới; **chưa có lịch tự cập nhật nền**.

## Việc liên quan: SCRUM-36 — seed key Redis

Đề bài còn yêu cầu **20–50 session/cache key trên Redis với TTL khác nhau**. Đây là
ticket riêng, viết script riêng (gợi ý `scripts/SeedRedis/seed_redis.py`). Key phải
theo đúng pattern trong `docs/redis-keyspace.md`:

```python
import redis, json
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

r.hset("session:demo-abc-123", mapping={"userId": "...", "username": "demo", "role": "user"})
r.expire("session:demo-abc-123", 1800)          # TTL khác nhau cho mỗi key để demo đếm lùi
r.set("post:<postId>", json.dumps({...}), ex=600)
r.set("post:<postId>:views", 42)                 # KHÔNG đặt TTL cho bộ đếm lượt xem
```

Đặt TTL lệch nhau (300s, 600s, 900s, 1800s...) để bước 3 kịch bản demo mở
RedisInsight chỉ ra được các key đang đếm lùi khác nhau.

---

Bảng phân công file và toàn bộ hợp đồng dữ liệu: `AGENTS.md` ở gốc repo.
