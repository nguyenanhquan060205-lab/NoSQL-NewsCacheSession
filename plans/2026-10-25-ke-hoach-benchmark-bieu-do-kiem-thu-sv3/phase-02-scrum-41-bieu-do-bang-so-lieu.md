---
phase: 2
ticket: SCRUM-41
title: "plot.py: biểu đồ so sánh thời gian tải + bảng số liệu"
status: pending
priority: P1
effort: "1.5h"
dependsOn: [1]
---

# Phase 02 — SCRUM-41: Biểu đồ + bảng số liệu

> Chế độ `--deep`: **scout lại trước khi code**. Đọc kết quả thật trong
> `results/…-chinh-thuc/` rồi mới chốt nên có biểu đồ nào (ví dụ S3 bão hòa ở concurrency 10
> thì bỏ mức 50 khỏi trục).

## Mục tiêu
`python scripts/Benchmark/plot.py results/<nhãn>` → `results/<nhãn>/charts/*.png` +
`results/<nhãn>/summary.md`. Chạy được **không cần API**, chỉ đọc file → chạy lại bao nhiêu lần cũng được.

## Phác thảo
| # | Biểu đồ | Nguồn | Ghi chú |
|---|---|---|---|
| 1 | Cột: median độ trễ của 3 loại, thanh lỗi đến p95, nhãn số trên đầu cột | `raw_latency.csv` | Biểu đồ chính, đặt đầu báo cáo và slide |
| 2 | Box plot phân bố 3 loại | `raw_latency.csv` | Cho thấy độ trễ HIT ổn định, MISS phân tán |
| 3 | Đường: độ trễ theo thứ tự lượt đo | `raw_latency.csv` | Chứng minh không có xu hướng trôi dần (drift) hay ảnh hưởng của warm-up |
| 4 | Cột đôi: RPS theo concurrency, HIT vs Không cache. Kèm p95 | `load.csv` | |
| 5 | Cột: stampede — 50 request vs số MISS (kỳ vọng 1) | `stampede.json` | Bằng chứng cho khóa `SET NX PX` |
| 6 | *(nếu có S4)* So sánh 101 bài vs 1.000 bài | 2 thư mục kết quả | |

- Nhãn tiếng Việt, font `DejaVu Sans` (có đủ dấu), `dpi=200`, nền trắng, không màu mè.
  Ba loại dùng một bộ màu cố định cho mọi biểu đồ.
- Chú thích bên dưới mỗi hình: ngày đo, số mẫu, số bài, máy đo (lấy từ `env.json`).
- `summary.md`: bảng Markdown (Loại | n | mean | median | p95 | p99 | min | max) + bảng tải + kết quả stampede,
  để dán thẳng vào chương báo cáo.

## Các bước
1. [ ] Nhánh `SCRUM-41-ve-bieu-do-so-sanh-thoi-gian-tai` tách từ nhánh SCRUM-40.
2. [ ] `test_plot.py` (unittest): tạo bộ kết quả giả trong thư mục tạm → `plot.py` tạo ra đủ file PNG
       (> 0 byte) và `summary.md` chứa đúng các con số median.
3. [ ] Viết `plot.py` (`matplotlib.use("Agg")`). Dùng lại `summarize`/`percentile` bằng cách import từ `benchmark.py`.
4. [ ] Chạy trên kết quả chính thức, **mở xem từng ảnh** (chữ có đủ dấu, không bị cắt nhãn).
5. [ ] Commit `feat(SCRUM-41): biểu đồ và bảng số liệu hiệu năng` kèm `charts/` của lần chạy chính thức.

## Tiêu chí đạt
- Test xanh. Có ≥ 4 PNG hiển thị đúng tiếng Việt.
- Số trong `summary.md` khớp `summary.json` (cùng một hàm tính ra).
