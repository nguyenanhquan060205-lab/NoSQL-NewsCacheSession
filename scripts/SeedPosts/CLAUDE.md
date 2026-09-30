# Script seed dữ liệu mẫu (SCRUM-32 — SV3 — Nguyễn Xuân Định)

Yêu cầu đề bài: **tối thiểu 100 bài viết hoàn chỉnh có tiêu đề, nội dung và hình
ảnh**. Phần này ăn 1.0đ trong barem.

## ⛔ Tên field phải là camelCase, và phải bọc ObjectId

Đây là chỗ dễ sai nhất của cả dự án. API C# ánh xạ document bằng đúng các tên dưới
đây (ép bằng `[BsonElement]` trong `Models/Post.cs`). **Ghi sai tên field thì insert
vẫn thành công nhưng API đọc ra bài viết rỗng tiêu đề, `createdAt = 01/01/0001`,
trang chủ trắng và sort sai** — và sẽ không ai hiểu vì sao.

Database `newsdb`, collection `posts` và `categories`.

```python
from pymongo import MongoClient
from bson import ObjectId
from faker import Faker
import random
from datetime import datetime, timezone

client = MongoClient("mongodb://localhost:27017")
db = client["newsdb"]
faker = Faker("vi_VN")

# 1) Chuyên mục trước — API tạo/sửa bài viết kiểm tra categoryId có tồn tại thật,
#    không có chuyên mục thì trả về 400.
db.categories.delete_many({})
categories = [
    {"name": "Thời sự",   "slug": "thoi-su",   "description": None, "createdAt": datetime.now(timezone.utc)},
    {"name": "Thể thao",  "slug": "the-thao",  "description": None, "createdAt": datetime.now(timezone.utc)},
    {"name": "Công nghệ", "slug": "cong-nghe", "description": None, "createdAt": datetime.now(timezone.utc)},
    {"name": "Giải trí",  "slug": "giai-tri",  "description": None, "createdAt": datetime.now(timezone.utc)},
    {"name": "Kinh doanh","slug": "kinh-doanh","description": None, "createdAt": datetime.now(timezone.utc)},
]
category_ids = db.categories.insert_many(categories).inserted_ids

# 2) 100 bài viết
db.posts.delete_many({})
posts = []
for i in range(100):
    title = faker.sentence(nb_words=8).rstrip(".")
    created = faker.date_time_this_year(tzinfo=timezone.utc)
    posts.append({
        "title": title,
        "slug": f"{slugify(title)}-{i}",              # slug phải UNIQUE (có unique index)
        "content": "\n\n".join(faker.paragraphs(nb=5)),
        "imageUrl": f"https://picsum.photos/seed/{i}/800/450",
        "categoryId": ObjectId(random.choice(category_ids)),   # ⛔ ObjectId, KHÔNG phải str
        "authorId": None,                              # None là hợp lệ với dữ liệu seed
        "views": random.randint(0, 500),
        "isDeleted": False,
        "deletedAt": None,
        "createdAt": created,
        "updatedAt": created,
    })
db.posts.insert_many(posts)
print(f"Đã nạp {len(category_ids)} chuyên mục và {len(posts)} bài viết vào newsdb.")
```

`slugify` cần bỏ dấu tiếng Việt và chỉ giữ `a-z0-9-` (dùng `unidecode` hoặc
`python-slugify`), giống hàm `ToSlug` trong `PostsController.cs`. Thêm hậu tố `-{i}`
vì `posts.slug` có **unique index** — trùng slug là `DuplicateKeyError` giữa lúc chạy.

## Tại sao phải `delete_many` trước

Dữ liệu test cũ (ghi trước 30/09/2026) dùng tên field PascalCase nên API không đọc
được nữa. Chạy lại seed mà không xóa thì trang chủ sẽ lẫn cả bài "hỏng" lẫn bài tốt.

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
