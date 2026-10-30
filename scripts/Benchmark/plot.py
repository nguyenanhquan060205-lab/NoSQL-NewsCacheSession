"""
Vẽ biểu đồ + bảng số liệu (SCRUM-41) từ một thư mục kết quả của benchmark.py.

Chỉ đọc file, không cần API — chạy lại bao nhiêu lần cũng ra cùng kết quả.

Cách chạy:
    python plot.py results/2026-10-25-chinh-thuc
Kết quả: results/<nhãn>/charts/*.png và results/<nhãn>/summary.md
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from benchmark import LOAI_HIT, LOAI_KHONG_CACHE, LOAI_MISS, LOAI_THU_TU, summarize  # noqa: E402

TEN_LOAI = {
    LOAI_KHONG_CACHE: "Không cache\n(MongoDB)",
    LOAI_MISS: "Cache MISS\n(MongoDB → Redis)",
    LOAI_HIT: "Cache HIT\n(Redis)",
}
MAU_LOAI = {LOAI_KHONG_CACHE: "#8a8a8a", LOAI_MISS: "#d9822b", LOAI_HIT: "#2b6cb0"}

CHART_FILES = [
    "01-do-tre-trung-vi.png",
    "02-phan-bo-do-tre.png",
    "03-do-tre-theo-luot.png",
    "04-tai-dong-thoi.png",
    "05-cache-stampede.png",
]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})


def fmt(value: float, digits: int = 2) -> str:
    """Số thập phân kiểu Việt Nam: 3.456 → '3,46'."""
    return f"{value:.{digits}f}".replace(".", ",")


def load_run(run_dir: Path) -> dict:
    with (run_dir / "raw_latency.csv").open(encoding="utf-8") as f:
        latency = [row for row in csv.DictReader(f) if row["valid"] == "True"]
    for row in latency:
        row["ms"] = float(row["ms"])
    with (run_dir / "load.csv").open(encoding="utf-8") as f:
        load = list(csv.DictReader(f))
    for row in load:
        for key in ("concurrency", "requests", "errors"):
            row[key] = int(row[key])
        for key in ("rps", "p50", "p95", "p99"):
            row[key] = float(row[key])

    def read_json(name):
        return json.loads((run_dir / name).read_text(encoding="utf-8"))

    samples = {loai: [row["ms"] for row in latency if row["loai"] == loai] for loai in LOAI_THU_TU}
    return {
        "latency": latency,
        "samples": samples,
        "stats": {loai: summarize(values) for loai, values in samples.items() if values},
        "load": load,
        "stampede": read_json("stampede.json"),
        "env": read_json("env.json"),
    }


def caption(run: dict, with_samples: bool = True) -> str:
    env = run["env"]
    total = f"{env['totalItems']:,}".replace(",", ".")
    parts = [f"Đo ngày {env['measuredAt'][:10]}"]
    if with_samples and LOAI_HIT in run["stats"]:
        parts.append(f"{run['stats'][LOAI_HIT]['n']} mẫu mỗi loại")
    parts += [f"{total} bài viết trong MongoDB", "API, MongoDB, Redis cùng một máy"]
    return " · ".join(parts)


def save(fig, run: dict, path: Path, with_samples: bool = True) -> None:
    fig.text(0.5, 0.005, caption(run, with_samples), ha="center", va="bottom", fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def chart_median(run: dict, path: Path) -> None:
    loai_list = [loai for loai in LOAI_THU_TU if loai in run["stats"]]
    medians = [run["stats"][loai]["median"] for loai in loai_list]
    p95 = [run["stats"][loai]["p95"] for loai in loai_list]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar([TEN_LOAI[loai] for loai in loai_list], medians,
                  color=[MAU_LOAI[loai] for loai in loai_list], width=0.55,
                  yerr=[[0] * len(medians), [p - m for p, m in zip(p95, medians)]],
                  capsize=6, error_kw={"ecolor": "#333333", "elinewidth": 1})
    for bar, median, top in zip(bars, medians, p95):
        ax.text(bar.get_x() + bar.get_width() / 2, top, f"{fmt(median)} ms",
                ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("Thời gian phản hồi (ms)")
    ax.set_title("Thời gian đọc một bài viết — trung vị (thanh lỗi: tới p95)")
    ax.set_ylim(0, max(p95) * 1.2)
    save(fig, run, path)


def chart_box(run: dict, path: Path) -> None:
    loai_list = [loai for loai in LOAI_THU_TU if run["samples"][loai]]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    box = ax.boxplot([run["samples"][loai] for loai in loai_list], patch_artist=True,
                     tick_labels=[TEN_LOAI[loai] for loai in loai_list], widths=0.5,
                     medianprops={"color": "black"})
    for patch, loai in zip(box["boxes"], loai_list):
        patch.set_facecolor(MAU_LOAI[loai])
        patch.set_alpha(0.75)
    ax.set_ylabel("Thời gian phản hồi (ms)")
    ax.set_title("Phân bố thời gian đọc bài viết")
    save(fig, run, path)


def chart_sequence(run: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for loai in LOAI_THU_TU:
        values = run["samples"][loai]
        if values:
            ax.plot(range(1, len(values) + 1), values, marker=".", linestyle="-", linewidth=0.8,
                    markersize=3, color=MAU_LOAI[loai], label=TEN_LOAI[loai].replace("\n", " "))
    ax.set_xlabel("Thứ tự lượt đo")
    ax.set_ylabel("Thời gian phản hồi (ms)")
    ax.set_title("Thời gian đọc theo từng lượt đo (kiểm tra độ ổn định)")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3)
    save(fig, run, path)


def chart_load(run: dict, path: Path) -> None:
    levels = sorted({row["concurrency"] for row in run["load"]})
    series = [loai for loai in (LOAI_KHONG_CACHE, LOAI_HIT)
              if any(row["loai"] == loai for row in run["load"])]
    width = 0.8 / len(series)
    fig, (ax_rps, ax_p95) = plt.subplots(1, 2, figsize=(10, 4.5))
    for i, loai in enumerate(series):
        rows = {row["concurrency"]: row for row in run["load"] if row["loai"] == loai}
        xs = [j + (i - (len(series) - 1) / 2) * width for j in range(len(levels))]
        label = TEN_LOAI[loai].replace("\n", " ")
        for ax, key in ((ax_rps, "rps"), (ax_p95, "p95")):
            values = [rows[level][key] for level in levels]
            bars = ax.bar(xs, values, width=width, color=MAU_LOAI[loai], label=label)
            for bar, value in zip(bars, values):
                text = f"{value:.0f}" if key == "rps" else fmt(value)
                ax.text(bar.get_x() + bar.get_width() / 2, value, text,
                        ha="center", va="bottom", fontsize=8)
    for ax, title, ylabel in ((ax_rps, "Thông lượng", "Request / giây"),
                              (ax_p95, "Độ trễ p95", "ms")):
        ax.set_xticks(range(len(levels)), [f"{level} luồng" for level in levels])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.25)
    ax_rps.legend(frameon=False, loc="upper left", ncol=2)
    fig.suptitle("Tải đồng thời: Cache HIT so với Không cache")
    save(fig, run, path, with_samples=False)


def chart_stampede(run: dict, path: Path) -> None:
    trials = run["stampede"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = range(len(trials))
    sent = ax.bar([x - 0.2 for x in xs], [t["requests"] for t in trials], width=0.4,
                  color="#8a8a8a", label="Request đồng thời gửi tới")
    miss = ax.bar([x + 0.2 for x in xs], [t["miss"] for t in trials], width=0.4,
                  color=MAU_LOAI[LOAI_MISS], label="Request phải đọc MongoDB (MISS)")
    for bars in (sent, miss):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.0f}",
                    ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(xs), [f"Lần {i + 1}" for i in xs])
    ax.set_ylabel("Số request")
    ax.set_title("Cache stampede: khóa SET NX PX chỉ cho 1 request đọc MongoDB")
    ax.set_ylim(0, max(t["requests"] for t in trials) * 1.3)
    ax.legend(frameon=False, loc="upper center", ncol=2)
    save(fig, run, path, with_samples=False)


def render_summary(run: dict) -> str:
    lines = ["# Kết quả đo hiệu năng", "", caption(run), "",
             "## Độ trễ tuần tự (ms)", "",
             "| Loại | n | Trung bình | Trung vị | p95 | p99 | Nhỏ nhất | Lớn nhất |",
             "|---|---|---|---|---|---|---|---|"]
    for loai, s in run["stats"].items():
        lines.append(f"| {TEN_LOAI[loai].replace(chr(10), ' ')} | {s['n']} | {fmt(s['mean'])} | "
                     f"{fmt(s['median'])} | {fmt(s['p95'])} | {fmt(s['p99'])} | "
                     f"{fmt(s['min'])} | {fmt(s['max'])} |")
    stats = run["stats"]
    if {LOAI_MISS, LOAI_HIT, LOAI_KHONG_CACHE} <= set(stats):
        hit = stats[LOAI_HIT]["median"]
        lines += ["", f"Theo trung vị: Cache MISS chậm hơn Cache HIT **{fmt(stats[LOAI_MISS]['median'] / hit)} lần**; "
                      f"Không cache chậm hơn Cache HIT **{fmt(stats[LOAI_KHONG_CACHE]['median'] / hit)} lần**."]

    lines += ["", "## Cache stampede", "",
              "| Lần | Request đồng thời | MISS (đọc MongoDB) | HIT | Lỗi | p95 (ms) |",
              "|---|---|---|---|---|---|"]
    for i, t in enumerate(run["stampede"], 1):
        lines.append(f"| {i} | {t['requests']} | {t['miss']}/{t['requests']} | {t['hit']} | "
                     f"{t['errors']} | {fmt(t['latency']['p95'])} |")

    lines += ["", "## Tải đồng thời", "",
              "| Loại | Luồng | Request | Lỗi | Request/giây | p50 (ms) | p95 (ms) | p99 (ms) |",
              "|---|---|---|---|---|---|---|---|"]
    for row in run["load"]:
        lines.append(f"| {TEN_LOAI[row['loai']].replace(chr(10), ' ')} | {row['concurrency']} | "
                     f"{row['requests']} | {row['errors']} | {fmt(row['rps'], 1)} | {fmt(row['p50'])} | "
                     f"{fmt(row['p95'])} | {fmt(row['p99'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Vẽ biểu đồ + bảng số liệu từ kết quả của benchmark.py.")
    parser.add_argument("run_dir", type=Path, help="Thư mục kết quả, ví dụ results/2026-10-25-chinh-thuc")
    run_dir = parser.parse_args(argv).run_dir
    if not (run_dir / "raw_latency.csv").is_file():
        parser.error(f"không thấy {run_dir / 'raw_latency.csv'} — đã chạy benchmark.py với --label này chưa?")
    run = load_run(run_dir)
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(exist_ok=True)

    for name, draw in zip(CHART_FILES, (chart_median, chart_box, chart_sequence,
                                        chart_load, chart_stampede)):
        draw(run, charts_dir / name)
    (run_dir / "summary.md").write_text(render_summary(run), encoding="utf-8")
    print(f"Đã vẽ {len(CHART_FILES)} biểu đồ vào {charts_dir} và ghi {run_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
