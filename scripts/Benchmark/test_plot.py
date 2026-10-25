import tempfile
import unittest
from pathlib import Path

import plot
from benchmark import LOAI_HIT, LOAI_KHONG_CACHE, LOAI_MISS, summarize, write_results


def fake_run(out_dir: Path) -> None:
    latency = []
    for round_no in range(1, 4):
        for loai, base in ((LOAI_KHONG_CACHE, 4.0), (LOAI_MISS, 9.0), (LOAI_HIT, 3.0)):
            latency.append({"round": round_no, "postId": "p1", "loai": loai,
                            "ms": base + round_no / 10, "status": 200,
                            "xCache": "" if loai == LOAI_KHONG_CACHE else loai[-4:].upper(),
                            "valid": True})
    # Mẫu không hợp lệ không được lọt vào biểu đồ hay bảng
    latency.append({"round": 3, "postId": "p1", "loai": LOAI_HIT, "ms": 999.0,
                    "status": 200, "xCache": "MISS", "valid": False})
    stampede = [{"postId": "p1", "requests": 50, "miss": 1, "hit": 49, "errors": 0,
                 "latency": summarize([1.0, 2.0, 3.0])}]
    load = [{"loai": loai, "concurrency": c, "requests": 100, "errors": 0, "seconds": 0.5,
             "rps": 200.0 * c, "p50": 1.0, "p95": 2.0, "p99": 3.0}
            for c in (1, 10) for loai in (LOAI_HIT, LOAI_KHONG_CACHE)]
    env = {"measuredAt": "2026-10-25T05:00:00+00:00", "totalItems": 10150,
           "config": {"posts": 1, "rounds": 3}}
    write_results(out_dir, latency=latency, stampede=stampede, load=load, env=env)


class PlotTests(unittest.TestCase):
    def test_fmt_uses_vietnamese_decimal_comma(self):
        self.assertEqual(plot.fmt(3.456), "3,46")

    def test_main_creates_charts_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            fake_run(run_dir)

            self.assertEqual(plot.main([str(run_dir)]), 0)

            charts = sorted(p.name for p in (run_dir / "charts").glob("*.png"))
            self.assertEqual(charts, sorted(plot.CHART_FILES))
            for name in charts:
                self.assertGreater((run_dir / "charts" / name).stat().st_size, 0)

            summary = (run_dir / "summary.md").read_text(encoding="utf-8")
            hit_median = summarize([3.1, 3.2, 3.3])["median"]
            self.assertIn(plot.fmt(hit_median), summary)
            self.assertIn("1/50", summary)
            self.assertNotIn("999", summary)
            self.assertIn("10.150 bài viết", summary)
            self.assertIn("API, MongoDB, Redis", summary)


if __name__ == "__main__":
    unittest.main()
