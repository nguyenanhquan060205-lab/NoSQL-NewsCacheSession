# Benchmark Cache-Aside (SCRUM-40)

Đo thời gian đọc một bài viết theo ba đường:

| Loại | Endpoint | Ý nghĩa |
|---|---|---|
| `khong-cache` | `GET /api/posts/slug/{slug}` | Đọc thẳng MongoDB, endpoint **cố ý không cache**, dùng làm mốc |
| `cache-miss` | `DEL post:{id}` rồi `GET /api/posts/{id}` | Lần đọc đầu: Redis không có → khóa → MongoDB → ghi lại Redis |
| `cache-hit` | `GET /api/posts/{id}` lần nữa | Đọc thẳng từ Redis |

Mỗi mẫu đều kiểm tra header `X-Cache`. Mẫu `cache-miss` mà nhận `HIT` (hoặc ngược lại)
bị đánh dấu `valid=false` và không tính vào thống kê.

## Chạy

Điều kiện: Docker (MongoDB + Redis) và API ở `http://localhost:5134` đã bật, DB có ≥ 100 bài.
Trên Windows, nếu máy có cài sẵn MongoDB dạng service thì phải `net stop MongoDB` trước
(chạy PowerShell quyền admin), nếu không API sẽ đọc nhầm MongoDB của Windows.

```powershell
python -m pip install -r scripts/Benchmark/requirements.txt
python scripts/Benchmark/benchmark.py --label 2026-10-25-chinh-thuc
```

Tham số hay dùng:

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `--posts` / `--rounds` | 20 / 10 | S1: số mẫu mỗi loại = posts × rounds |
| `--warmup` | 5 | Số lượt khởi động nóng, không ghi lại |
| `--stampede` / `--stampede-trials` | 50 / 5 | S2: số request đồng thời / số lần lặp |
| `--load-levels` / `--load-requests` | `1,10,50` / 500 | S3: các mức concurrency / số request mỗi mức |
| `--skip-stampede`, `--skip-load` | | Bỏ qua S2 / S3 |
| `--api`, `--redis` | `http://localhost:5134`, `redis://localhost:6379/0` | |

Chạy thử nhanh: `--posts 3 --rounds 2 --stampede 10 --stampede-trials 1 --load-requests 50 --label nhap`.

## Kết quả (`results/<nhãn>/`)

| File | Nội dung |
|---|---|
| `raw_latency.csv` | Từng mẫu S1: `round, postId, loai, ms, status, xCache, valid` |
| `stampede.json` | Mỗi lần S2: số MISS/HIT/lỗi và phân bố độ trễ |
| `load.csv` | S3: `loai, concurrency, requests, errors, seconds, rps, p50, p95, p99` |
| `summary.json` | Thống kê S1 theo loại (n, mean, median, p95, p99, min, max, stdev) + S2 + S3 |
| `env.json` | Máy đo, số bài, commit, cấu hình, `/api/cache/stats` trước/sau |

Chỉ thư mục `*-chinh-thuc` được commit (xem `.gitignore`).

## An toàn dữ liệu

Script chỉ chạy `DEL post:{id}` cho đúng bài đang đo, không `FLUSH`, `KEYS` hay `SCAN`.
`GET /api/posts/{id}` không tăng lượt xem, nên đo không làm thay đổi `views`.
Bộ đếm `/api/cache/stats` sẽ tăng theo số request đo; `env.json` ghi giá trị trước/sau.

## Test

```powershell
cd scripts/Benchmark
python -m unittest
```

## Giới hạn

- Client Python bị GIL giới hạn: ở concurrency cao, chính client có thể là nút cổ chai.
  S3 dùng để so **tương đối** HIT với Không cache, không phải đo giới hạn của server.
- API, MongoDB, Redis và client chạy trên cùng một máy.
