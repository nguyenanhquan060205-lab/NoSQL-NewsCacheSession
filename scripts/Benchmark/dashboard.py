"""
Dashboard HTML tương tác từ một thư mục kết quả của benchmark.py.

Chỉ đọc file, không cần API. File sinh ra tự chứa số liệu, mở thẳng bằng trình duyệt
(cần mạng để tải thư viện d3 từ cdnjs).

Cách chạy:
    python dashboard.py results/2026-10-25-chinh-thuc
Kết quả: results/<nhãn>/dashboard.html
"""

import csv
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).with_name("dashboard_template.html")
D3_URL = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"

TEN_LOAI = {
    "khong-cache": "Không cache (MongoDB)",
    "cache-miss": "Cache MISS (MongoDB → Redis)",
    "cache-hit": "Cache HIT (Redis)",
}

# Màu và kích thước chữ mà template dùng (biến CSS --cds-*, --color-*), có cả giao diện tối.
TOKENS = """
:root{--font-anthropic-sans:"Segoe UI",Roboto,Arial,sans-serif;--font-anthropic-serif:Georgia,"Noto Serif","Times New Roman",serif;
--cds-font-size-caption:.8125rem;--cds-font-size-body:.9375rem;--cds-font-size-heading:1.0625rem;--cds-font-size-title:2rem;--cds-font-weight-medium:600;
--cds-gap-xs:.25rem;--cds-gap-sm:.5rem;--cds-gap-md:1rem;--cds-gap-lg:1.5rem;--cds-gap-xl:2.25rem;
--cds-pad-xs:.25rem;--cds-pad-sm:.5rem;--cds-pad-md:1rem;--cds-pad-lg:1.25rem;--cds-radius:8px;--cds-dur-slow:.3s;
--color-bg:#f6f6f4;--color-panel:#ffffff;--color-fg:#1c1c1a;--color-fg-muted:#6b6a64;--color-border-line:#e3e2dc;
--color-ok:#2f7d4f;--color-warn:#a8660b;--color-bad:#c0392b;
--cds-chart-grid:#ecebe6;--cds-chart-axis:#b9b7ae;--cds-chart-reference:#8f8d84;
--cds-surface-popover:#ffffff;--cds-border:#dddcd5;--cds-shadow-popover:0 4px 16px rgba(0,0,0,.12);--cds-text-secondary:#6b6a64;
--s1:#c2410c;--s2:#2563eb;--s3:#9ca3af}
@media (prefers-color-scheme:dark){:root{--color-bg:#161615;--color-panel:#1f1f1d;--color-fg:#ecebe6;--color-fg-muted:#a3a29b;--color-border-line:#33322f;
--color-ok:#5fbf86;--color-warn:#e0a24a;--color-bad:#f07167;--cds-chart-grid:#2b2a27;--cds-chart-axis:#55534d;--cds-chart-reference:#77756d;
--cds-surface-popover:#262624;--cds-border:#3a3936;--cds-shadow-popover:0 4px 16px rgba(0,0,0,.5);--cds-text-secondary:#a3a29b;
--s1:#fb923c;--s2:#60a5fa;--s3:#8b8f97;color-scheme:dark}}
body{margin:0;background:var(--color-bg);color:var(--color-fg);font-family:var(--font-anthropic-sans)}
#dash-root{padding:2rem max(16px,4vw) 3rem}
.dash-skeleton{color:transparent}
"""

# Thay cho API dashboard: dữ liệu nằm sẵn trong DATA, mỗi phần tử data-draw được vẽ lại khi đổi kích thước.
SHIM = """
const DATA = __DATA__;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const draws = {};
const onDataFns = [];
window.dash = {
  get colors() { return ['--s1', '--s2', '--s3'].map(css); },
  data: (id) => (id in DATA ? {status: 'ok', data: DATA[id], columns: Object.keys(DATA[id][0] || {})} : {status: 'missing', data: []}),
  calc: (id, {inputs, fn}) => { DATA[id] = fn(...inputs.map((i) => DATA[i] || [])); },
  onData: (fn) => onDataFns.push(fn),
  draw: (name, fn) => { draws[name] = fn; },
};
function drawAll() {
  onDataFns.forEach((fn) => fn());
  document.querySelectorAll('[data-draw]').forEach((el) => draws[el.dataset.draw]?.(el));
}
window.addEventListener('DOMContentLoaded', () => {
  if (!window.d3) {
    document.getElementById('dash-root').prepend(Object.assign(document.createElement('p'), {
      textContent: 'Không tải được thư viện d3 — cần kết nối mạng để vẽ biểu đồ.', style: 'color:var(--color-bad)'}));
    return;
  }
  drawAll();
  let width = innerWidth;
  addEventListener('resize', () => { if (innerWidth !== width) { width = innerWidth; drawAll(); } });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', drawAll);
});
"""


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_data(result_dir: Path) -> dict:
    summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
    env = json.loads((result_dir / "env.json").read_text(encoding="utf-8"))
    stampede_path = result_dir / "stampede.json"
    stampede = json.loads(stampede_path.read_text(encoding="utf-8")) if stampede_path.exists() else summary.get("stampede", [])
    load_path = result_dir / "load.csv"
    config = env.get("config", {})

    lat = [
        {"loai": loai, "ten": TEN_LOAI.get(loai, loai), **{k: v[k] for k in ("n", "mean", "median", "p95", "p99", "min", "max", "stdev")}}
        for loai, v in summary["latency"].items()
    ]
    stampede_rows = [
        {"lan": i, "postId": t["postId"], "requests": t["requests"], "miss": t["miss"], "hit": t["hit"],
         "errors": t["errors"], "median": t["latency"]["median"], "p95": t["latency"]["p95"], "max": t["latency"]["max"]}
        for i, t in enumerate(stampede, 1)
    ]
    cachestats = [
        {"thoiDiem": label, **env[key]}
        for key, label in (("cacheStatsBefore", "truoc"), ("cacheStatsAfter", "sau")) if env.get(key)
    ]
    env_row = {
        "measuredAt": env.get("measuredAt"), "totalItems": env.get("totalItems"),
        "posts": config.get("posts"), "rounds": config.get("rounds"), "warmup": config.get("warmup"),
        "loadRequests": config.get("load_requests"), "stampedeRequests": config.get("stampede"),
        "stampedeTrials": config.get("stampede_trials"), "cpuCount": env.get("cpuCount"),
        "os": env.get("os"), "gitCommit": env.get("gitCommit"),
    }
    data = {"lat": lat, "raw": read_csv(result_dir / "raw_latency.csv"), "env": [env_row]}
    if load_path.exists():
        data["load"] = read_csv(load_path)
    if stampede_rows:
        data["stampede"] = stampede_rows
    if cachestats:
        data["cachestats"] = cachestats
    return data


def build(result_dir: Path) -> Path:
    data = load_data(result_dir)
    body = TEMPLATE.read_text(encoding="utf-8")
    # Chuỗi "</" trong JSON có thể đóng thẻ <script> sớm.
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (
        "<!doctype html>\n<html lang=\"vi\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>Benchmark NewsCacheSession · {result_dir.name}</title>\n"
        f"<style>{TOKENS}</style>\n"
        f"<script src=\"{D3_URL}\"></script>\n"
        f"<script>{SHIM.replace('__DATA__', data_json)}</script>\n"
        "</head>\n<body>\n<div id=\"dash-root\">\n"
        f"{body}\n</div>\n</body>\n</html>\n"
    )
    out = result_dir / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python dashboard.py <thư mục kết quả>")
        return 2
    result_dir = Path(sys.argv[1])
    if not (result_dir / "summary.json").exists():
        print(f"Không thấy summary.json trong {result_dir}")
        return 1
    print(f"Đã ghi {build(result_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
