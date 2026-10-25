import csv
import json
import tempfile
import unittest
from pathlib import Path

import benchmark
from benchmark import (
    LOAI_HIT,
    LOAI_KHONG_CACHE,
    LOAI_MISS,
    cache_key,
    percentile,
    preflight,
    run_latency,
    run_stampede,
    summarize,
    write_results,
)

API = "http://api.test"


class FakeResponse:
    def __init__(self, status=200, headers=None, payload=None):
        self.status_code = status
        self.headers = headers or {}
        self._payload = payload if payload is not None else {}
        self.content = json.dumps(self._payload).encode()

    def json(self):
        return self._payload


class FakeApi:
    """Giả lập API Cache-Aside: GET /{id} trả MISS nếu key vừa bị xóa, các lần sau trả HIT."""

    def __init__(self, redis, posts, x_cache=True, force_hit=False):
        self.redis = redis
        self.posts = posts
        self.x_cache = x_cache
        self.force_hit = force_hit
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append(url)
        path = url[len(API):]
        if path == "/health":
            return FakeResponse(200, payload={"status": "Healthy"})
        if path.startswith("/api/posts?"):
            items = [{"id": pid, "slug": f"bai-{pid}", "title": pid} for pid in self.posts]
            return FakeResponse(payload={"items": items, "totalItems": 120})
        if path == "/api/cache/stats":
            return FakeResponse(payload={"hits": 0, "misses": 0})
        if path.startswith("/api/posts/slug/"):
            return FakeResponse(payload={"id": "x"})
        post_id = path.rsplit("/", 1)[-1]
        key = cache_key(post_id)
        hit = self.force_hit or key in self.redis.store
        self.redis.store.add(key)
        headers = {"X-Cache": "HIT" if hit else "MISS"} if self.x_cache else {}
        return FakeResponse(headers=headers, payload={"id": post_id})


class FakeRedis:
    def __init__(self):
        self.store = set()
        self.commands = []

    def delete(self, key):
        self.commands.append(("delete", key))
        self.store.discard(key)
        return 1


class HelperTests(unittest.TestCase):
    def test_cache_key_matches_csharp_helper(self):
        self.assertEqual(cache_key("abc"), "post:abc")

    def test_percentile_interpolates_linearly(self):
        values = list(range(1, 101))
        self.assertAlmostEqual(percentile(values, 95), 95.05)
        self.assertAlmostEqual(percentile(values, 50), 50.5)
        self.assertEqual(percentile([7.0], 99), 7.0)

    def test_percentile_rejects_empty_list(self):
        with self.assertRaises(ValueError):
            percentile([], 50)

    def test_summarize_returns_all_statistics(self):
        result = summarize([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(result["n"], 4)
        self.assertAlmostEqual(result["mean"], 2.5)
        self.assertAlmostEqual(result["median"], 2.5)
        self.assertEqual(result["min"], 1.0)
        self.assertEqual(result["max"], 4.0)
        self.assertEqual(
            set(result), {"n", "mean", "median", "p95", "p99", "min", "max", "stdev"}
        )


class PreflightTests(unittest.TestCase):
    def test_preflight_stops_when_x_cache_header_is_missing(self):
        redis = FakeRedis()
        api = FakeApi(redis, ["p1"], x_cache=False)
        with self.assertRaises(SystemExit):
            preflight(api, API)

    def test_preflight_returns_total_items(self):
        api = FakeApi(FakeRedis(), ["p1"])
        self.assertEqual(preflight(api, API), 120)


class LatencyTests(unittest.TestCase):
    def test_run_latency_records_three_samples_per_post_and_round(self):
        redis = FakeRedis()
        api = FakeApi(redis, ["p1", "p2"])
        posts = [{"id": "p1", "slug": "bai-p1"}, {"id": "p2", "slug": "bai-p2"}]

        rows = run_latency(api, redis, API, posts, rounds=3, warmup=0)

        self.assertEqual(len(rows), 3 * 2 * 3)
        self.assertTrue(all(row["valid"] for row in rows))
        loai = [row["loai"] for row in rows[:3]]
        self.assertEqual(loai, [LOAI_KHONG_CACHE, LOAI_MISS, LOAI_HIT])

    def test_run_latency_only_deletes_post_cache_keys(self):
        redis = FakeRedis()
        api = FakeApi(redis, ["p1"])
        run_latency(api, redis, API, [{"id": "p1", "slug": "bai-p1"}], rounds=2, warmup=1)

        self.assertTrue(redis.commands)
        for command, key in redis.commands:
            self.assertEqual(command, "delete")
            self.assertRegex(key, r"^post:[^:]+$")

    def test_run_latency_marks_unexpected_cache_result_invalid(self):
        redis = FakeRedis()
        api = FakeApi(redis, ["p1"], force_hit=True)
        rows = run_latency(api, redis, API, [{"id": "p1", "slug": "bai-p1"}], rounds=1, warmup=0)

        miss_row = next(row for row in rows if row["loai"] == LOAI_MISS)
        self.assertFalse(miss_row["valid"])
        self.assertEqual(miss_row["xCache"], "HIT")


class StampedeTests(unittest.TestCase):
    def test_run_stampede_counts_miss_and_hit(self):
        redis = FakeRedis()
        api = FakeApi(redis, ["p1"])
        result = run_stampede(lambda: api, redis, API, "p1", concurrency=8)

        self.assertEqual(result["requests"], 8)
        self.assertEqual(result["miss"] + result["hit"], 8)
        self.assertGreaterEqual(result["miss"], 1)
        self.assertEqual(redis.commands, [("delete", "post:p1")])


class LoadTests(unittest.TestCase):
    def test_run_load_splits_requests_across_workers(self):
        api = FakeApi(FakeRedis(), ["p1"])
        result = benchmark.run_load(lambda: api, f"{API}/api/posts/slug/bai-p1",
                                    LOAI_KHONG_CACHE, concurrency=3, total=10)

        self.assertEqual(result["requests"], 10)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["concurrency"], 3)
        self.assertGreater(result["rps"], 0)


class WriteResultsTests(unittest.TestCase):
    def test_write_results_creates_readable_files(self):
        rows = [
            {"round": 1, "postId": "p1", "loai": LOAI_HIT, "ms": 1.5,
             "status": 200, "xCache": "HIT", "valid": True},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            write_results(
                out,
                latency=rows,
                stampede=[{"postId": "p1", "requests": 2, "miss": 1, "hit": 1}],
                load=[{"loai": LOAI_HIT, "concurrency": 1, "requests": 1, "errors": 0,
                       "rps": 10.0, "p50": 1.0, "p95": 1.0, "p99": 1.0}],
                env={"totalItems": 120},
            )

            with (out / "raw_latency.csv").open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, benchmark.LATENCY_FIELDS)
                self.assertEqual(len(list(reader)), 1)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["latency"][LOAI_HIT]["n"], 1)
            self.assertEqual(json.loads((out / "env.json").read_text(encoding="utf-8"))["totalItems"], 120)
            self.assertTrue((out / "stampede.json").exists())
            self.assertTrue((out / "load.csv").exists())


if __name__ == "__main__":
    unittest.main()
