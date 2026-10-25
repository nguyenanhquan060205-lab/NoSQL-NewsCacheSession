"""
Benchmark (SCRUM-40): So sánh thời gian đọc bài viết Không cache / Cache MISS / Cache HIT.

Ba kịch bản:
  S1. Độ trễ tuần tự — mỗi vòng, mỗi bài: GET /slug (không cache) → DEL post:{id} →
      GET /{id} (kỳ vọng MISS) → GET /{id} (kỳ vọng HIT). Kiểm header X-Cache từng mẫu.
  S2. Cache stampede — DEL post:{id} rồi bắn N request đồng thời; khóa SET NX PX phải
      chặn để chỉ 1 request đọc MongoDB (kỳ vọng đúng 1 MISS).
  S3. Tải đồng thời — concurrency 1/10/50, so RPS và p95 giữa HIT và Không cache.

Script chỉ xóa đúng key `post:{id}` của bài đang đo, không FLUSH, không SCAN.

Yêu cầu: pip install -r requirements.txt
Cách chạy (API, MongoDB, Redis đã bật):
    cd scripts/Benchmark
    python benchmark.py --label 2026-10-25-chinh-thuc
Vẽ biểu đồ từ kết quả: python plot.py results/<nhãn>
"""

import argparse
import csv
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_API = "http://localhost:5134"
DEFAULT_REDIS = "redis://localhost:6379/0"
TIMEOUT_SECONDS = 10

LOAI_KHONG_CACHE = "khong-cache"
LOAI_MISS = "cache-miss"
LOAI_HIT = "cache-hit"
LOAI_THU_TU = [LOAI_KHONG_CACHE, LOAI_MISS, LOAI_HIT]

LATENCY_FIELDS = ["round", "postId", "loai", "ms", "status", "xCache", "valid"]
LOAD_FIELDS = ["loai", "concurrency", "requests", "errors", "seconds", "rps",
               "p50", "p95", "p99"]


def cache_key(post_id: str) -> str:
    """Khớp helper CacheKey(id) trong PostsController.cs — không ghép key ở chỗ khác."""
    return f"post:{post_id}"


def percentile(values, p: float) -> float:
    """Phân vị p (0–100), nội suy tuyến tính giữa hai mẫu kề nhau."""
    if not values:
        raise ValueError("Không có mẫu nào để tính phân vị.")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p / 100
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def summarize(samples) -> dict:
    return {
        "n": len(samples),
        "mean": statistics.fmean(samples),
        "median": statistics.median(samples),
        "p95": percentile(samples, 95),
        "p99": percentile(samples, 99),
        "min": min(samples),
        "max": max(samples),
        "stdev": statistics.stdev(samples) if len(samples) > 1 else 0.0,
    }


def timed_get(session, url: str):
    """Trả (ms, status, X-Cache). Đồng hồ dừng sau khi đã nhận hết body."""
    start = time.perf_counter()
    response = session.get(url, timeout=TIMEOUT_SECONDS)
    _ = response.content
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms, response.status_code, response.headers.get("X-Cache", "")


def preflight(session, api: str) -> int:
    """Kiểm tra API sẵn sàng đo; trả về tổng số bài viết."""
    health = session.get(f"{api}/health", timeout=TIMEOUT_SECONDS)
    if health.status_code != 200:
        raise SystemExit(f"API chưa khỏe (/health trả {health.status_code}). Bật Docker + API rồi chạy lại.")

    page = session.get(f"{api}/api/posts?page=1&pageSize=1", timeout=TIMEOUT_SECONDS).json()
    total = int(page.get("totalItems", 0))
    if total < 100 or not page.get("items"):
        raise SystemExit(f"Mới có {total} bài viết — cần ≥ 100 bài. Chạy scripts/SeedPosts/seed.py trước.")

    post_id = page["items"][0]["id"]
    probe = session.get(f"{api}/api/posts/{post_id}", timeout=TIMEOUT_SECONDS)
    if probe.headers.get("X-Cache") not in ("HIT", "MISS"):
        raise SystemExit("GET /api/posts/{id} không trả header X-Cache — báo SV2 kiểm tra GetById.")
    return total


def pick_posts(session, api: str, count: int):
    """Lấy `count` bài đầu trang chủ, thứ tự cố định để các lần chạy so sánh được."""
    page = session.get(f"{api}/api/posts?page=1&pageSize={count}", timeout=TIMEOUT_SECONDS).json()
    posts = [{"id": item["id"], "slug": item["slug"]} for item in page["items"]]
    if len(posts) < count:
        raise SystemExit(f"Chỉ lấy được {len(posts)}/{count} bài để đo.")
    return posts


def run_latency(session, redis_client, api: str, posts, rounds: int, warmup: int):
    """S1 — đo tuần tự ba loại, xen kẽ trong cùng một vòng để công bằng."""

    def measure_post(post, round_no, record):
        no_cache = timed_get(session, f"{api}/api/posts/slug/{post['slug']}")
        redis_client.delete(cache_key(post["id"]))
        miss = timed_get(session, f"{api}/api/posts/{post['id']}")
        hit = timed_get(session, f"{api}/api/posts/{post['id']}")
        if not record:
            return []
        rows = []
        for loai, (ms, status, x_cache), expected in (
            (LOAI_KHONG_CACHE, no_cache, None),
            (LOAI_MISS, miss, "MISS"),
            (LOAI_HIT, hit, "HIT"),
        ):
            valid = status == 200 and (expected is None or x_cache == expected)
            rows.append({"round": round_no, "postId": post["id"], "loai": loai,
                         "ms": round(ms, 3), "status": status, "xCache": x_cache,
                         "valid": valid})
        return rows

    # Khởi động nóng: JIT .NET, connection pool MongoDB/Redis — không ghi lại
    for _ in range(warmup):
        measure_post(posts[0], 0, record=False)

    rows = []
    for round_no in range(1, rounds + 1):
        for post in posts:
            rows.extend(measure_post(post, round_no, record=True))
        print(f"  S1 vòng {round_no}/{rounds} xong")
    return rows


def run_stampede(session_factory, redis_client, api: str, post_id: str, concurrency: int):
    """S2 — xóa cache rồi bắn `concurrency` request cùng lúc vào một bài."""
    redis_client.delete(cache_key(post_id))
    barrier = threading.Barrier(concurrency)
    url = f"{api}/api/posts/{post_id}"

    def worker(_):
        session = session_factory()
        barrier.wait()
        return timed_get(session, url)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(worker, range(concurrency)))

    latencies = [ms for ms, _, _ in results]
    return {
        "postId": post_id,
        "requests": concurrency,
        "miss": sum(1 for _, _, x in results if x == "MISS"),
        "hit": sum(1 for _, _, x in results if x == "HIT"),
        "errors": sum(1 for _, status, _ in results if status != 200),
        "latency": summarize(latencies),
    }


def run_load(session_factory, url: str, loai: str, concurrency: int, total: int):
    """S3 — `total` request chia đều cho `concurrency` luồng, mỗi luồng giữ một Session."""
    barrier = threading.Barrier(concurrency + 1)
    per_worker = [total // concurrency + (1 if i < total % concurrency else 0)
                  for i in range(concurrency)]

    def worker(count):
        session = session_factory()
        timed_get(session, url)  # mở kết nối trước, không tính
        barrier.wait()
        return [timed_get(session, url) for _ in range(count)]

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker, count) for count in per_worker]
        barrier.wait()
        start = time.perf_counter()
        results = [r for future in futures for r in future.result()]
        seconds = time.perf_counter() - start

    ok = [ms for ms, status, _ in results if status == 200]
    return {
        "loai": loai,
        "concurrency": concurrency,
        "requests": len(results),
        "errors": len(results) - len(ok),
        "seconds": round(seconds, 3),
        "rps": round(len(ok) / seconds, 1),
        "p50": round(percentile(ok, 50), 3),
        "p95": round(percentile(ok, 95), 3),
        "p99": round(percentile(ok, 99), 3),
    }


def latency_summary(rows) -> dict:
    result = {}
    for loai in LOAI_THU_TU:
        samples = [row["ms"] for row in rows if row["loai"] == loai and row["valid"]]
        if samples:
            result[loai] = summarize(samples)
    return result


def collect_env(api: str, total_items: int, args: argparse.Namespace) -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    return {
        "measuredAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "api": api,
        "totalItems": total_items,
        "os": platform.platform(),
        "cpu": platform.processor(),
        "cpuCount": os.cpu_count(),
        "python": platform.python_version(),
        "gitCommit": commit,
        "config": {key: value for key, value in vars(args).items() if key != "out"},
    }


def write_results(out_dir: Path, latency, stampede, load, env) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "raw_latency.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LATENCY_FIELDS)
        writer.writeheader()
        writer.writerows(latency)
    with (out_dir / "load.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOAD_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(load)

    summary = {
        "latency": latency_summary(latency),
        "invalidSamples": sum(1 for row in latency if not row["valid"]),
        "stampede": stampede,
        "load": load,
    }

    def dump(name, data):
        (out_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    dump("summary.json", summary)
    dump("stampede.json", stampede)
    dump("env.json", env)


def print_summary(latency_rows, stampede, load) -> None:
    summary = latency_summary(latency_rows)
    print("\n=== S1 — ĐỘ TRỄ TUẦN TỰ (ms) ===")
    print(f"{'Loại':<12} {'n':>4} {'mean':>8} {'median':>8} {'p95':>8} {'min':>8} {'max':>8}")
    for loai, s in summary.items():
        print(f"{loai:<12} {s['n']:>4} {s['mean']:>8.2f} {s['median']:>8.2f} "
              f"{s['p95']:>8.2f} {s['min']:>8.2f} {s['max']:>8.2f}")
    invalid = sum(1 for row in latency_rows if not row["valid"])
    print(f"Mẫu không hợp lệ (sai X-Cache / lỗi HTTP): {invalid}")
    if LOAI_MISS in summary and LOAI_HIT in summary:
        hit = summary[LOAI_HIT]["median"]
        print(f"→ Median: MISS/HIT = {summary[LOAI_MISS]['median'] / hit:.2f} lần, "
              f"Không cache/HIT = {summary[LOAI_KHONG_CACHE]['median'] / hit:.2f} lần")

    if stampede:
        print("\n=== S2 — CACHE STAMPEDE ===")
        for trial in stampede:
            print(f"  bài {trial['postId']}: MISS = {trial['miss']}/{trial['requests']}, "
                  f"lỗi = {trial['errors']}, p95 = {trial['latency']['p95']:.2f} ms")

    if load:
        print("\n=== S3 — TẢI ĐỒNG THỜI ===")
        for row in load:
            print(f"  {row['loai']:<12} c={row['concurrency']:<3} {row['rps']:>8.1f} req/s  "
                  f"p95 = {row['p95']:.2f} ms  lỗi = {row['errors']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đo hiệu năng Cache-Aside: Không cache / MISS / HIT.")
    parser.add_argument("--api", default=DEFAULT_API, help="Địa chỉ API (mặc định: %(default)s)")
    parser.add_argument("--redis", default=DEFAULT_REDIS, help="URL Redis (mặc định: %(default)s)")
    parser.add_argument("--posts", type=int, default=20, help="Số bài dùng để đo S1")
    parser.add_argument("--rounds", type=int, default=10, help="Số vòng S1 (mẫu/loại = posts × rounds)")
    parser.add_argument("--warmup", type=int, default=5, help="Số lượt khởi động nóng, không ghi lại")
    parser.add_argument("--stampede", type=int, default=50, help="Số request đồng thời ở S2")
    parser.add_argument("--stampede-trials", type=int, default=5, help="Số lần lặp S2 (mỗi lần một bài)")
    parser.add_argument("--load-levels", default="1,10,50", help="Các mức concurrency S3")
    parser.add_argument("--load-requests", type=int, default=500, help="Số request mỗi mức S3")
    parser.add_argument("--skip-stampede", action="store_true", help="Bỏ qua S2")
    parser.add_argument("--skip-load", action="store_true", help="Bỏ qua S3")
    parser.add_argument("--label", default=datetime.now().strftime("%Y-%m-%d-%H%M%S"),
                        help="Tên thư mục kết quả trong --out")
    parser.add_argument("--out", default=str(Path(__file__).parent / "results"),
                        help="Thư mục chứa kết quả")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()

    import redis
    import requests

    api = args.api.rstrip("/")
    session = requests.Session()
    redis_client = redis.Redis.from_url(args.redis)
    redis_client.ping()

    total_items = preflight(session, api)
    posts = pick_posts(session, api, max(args.posts, args.stampede_trials))
    print(f"API sẵn sàng — {total_items} bài viết. Đo {args.posts} bài × {args.rounds} vòng.")

    stats_before = session.get(f"{api}/api/cache/stats", timeout=TIMEOUT_SECONDS).json()
    latency = run_latency(session, redis_client, api, posts[:args.posts], args.rounds, args.warmup)

    stampede = []
    if not args.skip_stampede:
        for post in posts[:args.stampede_trials]:
            stampede.append(run_stampede(requests.Session, redis_client, api, post["id"], args.stampede))
            print(f"  S2 bài {post['id']} xong")

    load = []
    if not args.skip_load:
        target = posts[0]
        timed_get(session, f"{api}/api/posts/{target['id']}")  # đảm bảo key đang nóng cho HIT
        for level in (int(x) for x in args.load_levels.split(",")):
            for loai, url in ((LOAI_HIT, f"{api}/api/posts/{target['id']}"),
                              (LOAI_KHONG_CACHE, f"{api}/api/posts/slug/{target['slug']}")):
                load.append(run_load(requests.Session, url, loai, level, args.load_requests))
                print(f"  S3 {loai} c={level} xong")

    stats_after = session.get(f"{api}/api/cache/stats", timeout=TIMEOUT_SECONDS).json()
    env = collect_env(api, total_items, args)
    env["cacheStatsBefore"] = stats_before
    env["cacheStatsAfter"] = stats_after

    out_dir = Path(args.out) / args.label
    write_results(out_dir, latency, stampede, load, env)
    print_summary(latency, stampede, load)
    print(f"\nĐã lưu kết quả: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
