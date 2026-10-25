---
phase: 1
ticket: SCRUM-40
title: "Script benchmark: Không cache / Cache MISS / Cache HIT + stampede + tải đồng thời"
status: completed
priority: P1
effort: "3.5h"
dependsOn: []
---

# Phase 01 — SCRUM-40: Script benchmark

## Mục tiêu
Viết `scripts/Benchmark/benchmark.py` để chạy lại được, kiểm chứng được từng mẫu đo, và xuất
dữ liệu thô cho phase 2–3.

## Đã scout (ngày 25/10, `main` @ `bab6a5c`)
- `GET /api/posts/{id}` (SV2) gắn `X-Cache: HIT|MISS` qua `MarkCacheResult`. Khi MISS, request
  lấy lock `lock:post:{id}` (`SET NX PX 5000`). Request không lấy được lock thì
  `Task.Delay(50)` rồi gọi lại `GetById` (đệ quy) → khi stampede, mọi waiter đều trả `HIT`.
- `GET /api/posts/slug/{slug}` **cố ý không cache** → dùng làm mốc "Không cache".
- `GET /api/posts?page=&pageSize=` trả `items[]` (có `id`, `slug`) và `totalItems`.
- `GET /api/cache/stats` (SV2) → đếm hit/miss. `GET /health` → tình trạng MongoDB/Redis.
- `GetById` **không** tăng lượt xem (lượt xem đi qua `POST /{id}/view`) → đo không làm bẩn `views`.
- API chạy ở `http://localhost:5134` (launchSettings), Redis ở `localhost:6379`.
- Python 3.12.4. Đã có `requests`, `matplotlib`, `redis`. Không có `k6`/`ab`.
- Style test của SV3: `unittest` (xem `scripts/SeedPosts/test_seed.py`). Comment viết tiếng Việt.

## File
| File | Việc |
|---|---|
| `scripts/Benchmark/benchmark.py` | Viết lại toàn bộ khung TODO |
| `scripts/Benchmark/test_benchmark.py` | Mới — unit test cho các hàm thuần, HTTP/Redis dùng giả lập (fake) |
| `scripts/Benchmark/requirements.txt` | `requests>=2.31`, `redis>=5.0`, `matplotlib>=3.8` |
| `scripts/Benchmark/README.md` | Cách chạy, tham số, giải thích từng file kết quả |
| `scripts/Benchmark/.gitignore` | `results/*` trừ thư mục chính thức (`!results/2026-10-*-chinh-thuc/`) |

## Thiết kế `benchmark.py`

### CLI
```
python benchmark.py [--api http://localhost:5134] [--redis redis://localhost:6379/0]
                    [--posts 20] [--rounds 10] [--warmup 5]
                    [--stampede 50] [--load-levels 1,10,50] [--load-requests 500]
                    [--skip-load] [--skip-stampede] [--label <tên>] [--out results]
```
Mặc định: 20 bài × 10 vòng = **200 mẫu cho mỗi loại**.

### Hàm (thuần → dễ test)
| Hàm | Việc |
|---|---|
| `cache_key(post_id) -> "post:{id}"` | Helper key **duy nhất**, khớp `CacheKey()` của C#. Không ghép chuỗi ở chỗ khác. |
| `percentile(values, p)` | Nội suy tuyến tính, không cần numpy |
| `summarize(samples) -> {n, mean, median, p95, p99, min, max, stdev}` | |
| `timed_get(session, url) -> (ms, status, x_cache)` | Dùng `time.perf_counter()` bao quanh `session.get`. Đọc hết body (`r.content`) trước khi dừng đồng hồ. |
| `preflight(session, api)` | `/health` phải Healthy. `totalItems >= 100`. Gọi thử `GET /{id}` thấy header `X-Cache`, thiếu thì `SystemExit` với thông báo báo SV2. |
| `pick_posts(session, api, n)` | Lấy n bài đầu (id, slug), cố định thứ tự để chạy lại cho giống |
| `run_latency(...)` (S1) | Mỗi vòng, mỗi bài: `slug` → `DEL cache_key` → `GET id` (kỳ vọng MISS) → `GET id` (kỳ vọng HIT). Mẫu sai kỳ vọng thì ghi `valid=False`, không đưa vào thống kê. |
| `run_stampede(...)` (S2) | `DEL`, rồi `ThreadPoolExecutor(n)` + `threading.Barrier(n)` để bắn cùng lúc. Mỗi luồng dùng một `Session` riêng. Đếm số MISS/HIT, ghi lại độ trễ, đọc `/api/cache/stats` trước và sau. |
| `run_load(...)` (S3) | Mỗi mức concurrency c: tổng `--load-requests` request chia cho c luồng, đo HIT (key đã nóng) và Không cache (`slug`). Tính RPS = tổng/thời_gian_chạy, cùng p50/p95/p99. |
| `collect_env(session, api)` | OS, CPU (`platform`), Python, `totalItems`, thời điểm, cấu hình CLI, git commit (`git rev-parse --short HEAD`) |
| `write_results(dir, ...)` | `raw_latency.csv` (round, postId, loai, ms, status, xCache, valid) · `stampede.json` · `load.csv` · `summary.json` · `env.json` |
| `main()` | `sys.stdout.reconfigure(encoding="utf-8")` (giống seed.py), in bảng tóm tắt tiếng Việt và tỉ lệ `MISS/HIT`, `KhôngCache/HIT` |

### Quy tắc đo (chống sai số)
- Một `requests.Session` cho S1 → keep-alive, loại chi phí bắt tay TCP mà cách đo bằng `curl.exe` mắc phải.
- Warm-up `--warmup` lượt cho từng loại, không ghi lại (JIT .NET, connection pool của Mongo).
- Không `print` bên trong vòng đo, chỉ in tiến độ sau mỗi vòng.
- Tên loại cố định: `khong-cache`, `cache-miss`, `cache-hit` (plot.py và báo cáo dùng chung).

## Các bước (TDD)
1. [ ] `git checkout main && git pull` → `git checkout -b SCRUM-40-benchmark-apache-bench-k6-lan-1-vs-lan-2`.
2. [ ] Viết `test_benchmark.py` trước (đỏ):
   - `cache_key("abc") == "post:abc"`.
   - `percentile([1..100], 95) ≈ 95.05`. List một phần tử. List rỗng → `ValueError`.
   - `summarize` trả đủ khóa, đúng giá trị trên dữ liệu cố định.
   - `run_latency` với HTTP fake (trả `X-Cache` theo kịch bản) + Redis fake:
     a) đúng 3 mẫu mỗi (vòng × bài); b) Redis fake chỉ nhận lệnh `delete` với key dạng `post:*`;
     c) MISS mà trả `HIT` → `valid=False`.
   - `preflight` gặp response thiếu `X-Cache` → `SystemExit`.
   - `write_results` (thư mục tạm) → CSV đúng header, JSON đọc lại được.
3. [ ] Viết code cho tới khi `python -m unittest` xanh.
4. [ ] Chạy thử nhỏ: `--posts 3 --rounds 2 --stampede 10 --load-requests 50 --label nhap`.
5. [ ] Kiểm tra bằng RedisInsight: sau khi chạy chỉ có `post:*` bị làm mới. `session:*` và `posts:ver` giữ nguyên.
6. [ ] **Lần chạy chính thức** trên máy demo: đóng trình duyệt/IDE nặng, cắm sạc, chạy với mặc định,
       `--label 2026-10-25-chinh-thuc`. Ghi lại cấu hình máy.
7. [ ] Viết README.md. Commit `feat(SCRUM-40): script đo hiệu năng cache-aside, stampede và tải đồng thời`
       kèm thư mục `results/…-chinh-thuc`.

## Tiêu chí đạt
- `python -m unittest` (trong `scripts/Benchmark`) xanh.
- Lần chạy chính thức: ≥ 200 mẫu hợp lệ cho mỗi loại, tỉ lệ mẫu không hợp lệ < 1%.
- S2: in ra `MISS = x / 50`. Kỳ vọng x = 1.
- Không có lệnh Redis nào ngoài `DEL post:{id}` (có test khóa chặt).

## Tùy chọn (chỉ khi còn thời gian)
- **S4 — 1.000 bài:** `python scripts/SeedPosts/seed.py --count 1000` → chạy `--label …-1000bai`
  → khôi phục DB bằng `restore_full_data.ps1`.
- **k6:** `scripts/Benchmark/load.k6.js` chạy bằng
  `docker run --rm -i grafana/k6 run -e API=http://host.docker.internal:5134 - < load.k6.js`.
  Lưu ý: đi qua mạng Docker sẽ cộng thêm độ trễ, chỉ dùng để đối chiếu RPS.
