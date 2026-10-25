---
title: "Kế hoạch SV3: Benchmark, biểu đồ và chương kiểm thử hiệu năng (SCRUM-40/41/42)"
description: "Đo thật thời gian đọc bài viết Không cache / Cache MISS / Cache HIT, vẽ biểu đồ và viết chương kiểm thử hiệu năng để lấp phần 4 barem (2.5đ) đang 🔴."
status: in-progress
priority: P1
effort: "7.5h"
branch: SCRUM-40-benchmark-apache-bench-k6-lan-1-vs-lan-2
tags: [benchmark, python, redis, mongodb, matplotlib, docs, tdd]
blockedBy: []
blocks: []
created: "2026-10-25"
---

# Kế hoạch SV3 — Benchmark · Biểu đồ · Chương kiểm thử hiệu năng

**Người làm:** Nguyễn Xuân Định (SV3) · **Chế độ:** `--deep` (phase 1 chi tiết, phase 2–3
được scout lại trước khi code).

## 1. Bối cảnh — vì sao việc này là P1

- `docs/checklist-barem.md` chấm **Phần 4 (Kiểm thử hiệu năng & Demo, 2.5đ) là 🔴 Hổng**:
  "chưa có số đo, chưa có biểu đồ". Ước giữ được **1.0–1.5đ**, hạn ghi 23–24/10 → **đã trễ**.
- `scripts/Benchmark/benchmark.py` vẫn là khung rỗng từ commit `86eaff6`.
- Mục 5 trong báo cáo của SV2 (`docs/bao-cao-nguyen-ly-cache-aside.md`) đang chờ số đo của SV3.
- Như đã đo thử bằng PowerShell + `curl.exe` (`docs/kich-ban-demo-va-do-hieu-nang.md` B4):
  không cache 5,95 ms · MISS 14,15 ms · HIT 4,61 ms. Mỗi lần gọi `curl.exe` là một tiến trình
  mới và một kết nối TCP mới, nên khoảng 3–4 ms trong mỗi con số là chi phí cố định. Đo tải
  đồng thời bằng nhiều `curl` thì **thất bại**: kết quả bị chi phí khởi tạo tiến trình nuốt mất.

→ Plan này thay cách đo đó bằng **một script Python có thể chạy lại**: dùng keep-alive,
khởi động nóng (warm-up), lấy nhiều mẫu, kiểm chứng header `X-Cache` cho từng mẫu, rồi
xuất dữ liệu thô để vẽ biểu đồ và viết báo cáo.

## 2. Kết quả cần đạt (Outcome)

1. `python scripts/Benchmark/benchmark.py` chạy một lệnh ra thư mục `results/<nhãn>/` gồm số
   liệu thô + tóm tắt + thông tin môi trường đo.
2. `python scripts/Benchmark/plot.py results/<nhãn>` ra ≥ 4 biểu đồ PNG + bảng Markdown.
3. `docs/bao-cao-kiem-thu-hieu-nang.md` là chương báo cáo hoàn chỉnh với **số đo thật**, có
   phân tích và giới hạn của phép đo. Số liệu không được chỉnh cho đẹp.

## 3. Phân công file — chỉ đụng file SV3

| File | Trạng thái | Phase |
|---|---|---|
| `scripts/Benchmark/benchmark.py` | Sửa (SV3 sở hữu) | 1 |
| `scripts/Benchmark/test_benchmark.py` | Mới | 1 |
| `scripts/Benchmark/requirements.txt` | Mới | 1 |
| `scripts/Benchmark/README.md` | Mới | 1 |
| `scripts/Benchmark/.gitignore` | Mới (bỏ qua các lần chạy nháp) | 1 |
| `scripts/Benchmark/plot.py`, `test_plot.py` | Mới | 2 |
| `scripts/Benchmark/results/<nhãn-chính-thức>/**` | Mới (commit đúng **một** lần chạy chính thức) | 1–2 |
| `docs/bao-cao-kiem-thu-hieu-nang.md` | Mới (chương của SV3) | 3 |
| `docs/assets/kiem-thu-hieu-nang/*.png` | Mới | 3 |

**Không sửa** (chỉ nhắn chủ sở hữu):
- `PostsController.cs`, `RedisCacheService.cs` → SV2 (Quân). Benchmark chỉ **đọc** header `X-Cache`.
- `docs/bao-cao-nguyen-ly-cache-aside.md` mục 5 → SV2 tự điền số (SV3 gửi link chương).
- `docs/nosql-jira-tasks.csv`, `docs/checklist-barem.md`, `docs/kich-ban-demo-va-do-hieu-nang.md` → SV1 (Như).

## 4. Kiến trúc phép đo

```
benchmark.py ──HTTP keep-alive (requests.Session)──► API :5134 ──► Redis :6379 / MongoDB :27017
     │                                                   ▲
     └──redis-py: DEL post:{id} (chỉ key bài đang đo)───┘
     │
     └──► results/<nhãn>/ raw_latency.csv · stampede.json · load.csv · summary.json · env.json
                                    │
plot.py ◄───────────────────────────┘ ──► charts/*.png · summary.md  ──► chương báo cáo
```

Bốn kịch bản đo:

| # | Kịch bản | Câu hỏi trả lời | Ticket |
|---|---|---|---|
| S1 | Độ trễ tuần tự: Không cache (`/slug/{slug}`) · MISS (`DEL` rồi `GET /{id}`) · HIT (`GET /{id}` lần 2) | "Lần 1 vs lần 2 nhanh hơn bao nhiêu?" | 40 |
| S2 | Cache stampede: `DEL` rồi bắn 50 request đồng thời vào một bài | "Khóa `SET NX PX` có chặn được dồn xuống MongoDB không?" (kỳ vọng đúng **1** MISS) | 40 |
| S3 | Tải đồng thời: concurrency 1/10/50, so HIT với Không cache | "Chịu được bao nhiêu request/giây, p95 ra sao?" | 40 |
| S4 | *(tùy chọn)* Lặp S1 ở 1.000 bài | "Dữ liệu lớn hơn thì khoảng cách có giãn ra không?" | 40 |

## 5. Các phase

| Phase | Ticket | Nội dung | Effort | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|
| [01](phase-01-scrum-40-benchmark-script.md) | SCRUM-40 | Script benchmark + test + 1 lần chạy chính thức | 3.5h | — | completed |
| [02](phase-02-scrum-41-bieu-do-bang-so-lieu.md) | SCRUM-41 | `plot.py`: biểu đồ + bảng số liệu | 1.5h | 01 | completed |
| [03](phase-03-scrum-42-chuong-kiem-thu-hieu-nang.md) | SCRUM-42 | Chương báo cáo kiểm thử hiệu năng + bàn giao | 2.5h | 01, 02 | pending |

**Git:** tách nhánh từ `main` mới nhất. Mỗi ticket một nhánh, nhánh sau tách từ nhánh trước:
`SCRUM-40-…` → `SCRUM-41-…` → `SCRUM-42-…`. Commit tiếng Việt, ví dụ
`feat(SCRUM-40): script đo hiệu năng cache-aside`. **Không push khi chưa được đồng ý.**

## 6. Rủi ro & cách xử lý (red-team)

| Góc nhìn | Rủi ro | Xử lý |
|---|---|---|
| Giả định | API chưa trả header `X-Cache` → không phân biệt được HIT/MISS | Kiểm tra lúc khởi động (preflight). Thiếu header thì dừng với thông báo rõ. Mẫu nào có `X-Cache` sai kỳ vọng thì loại và đếm lại. |
| Giả định | "200 ms vs 5 ms" của đề bài không tái hiện được trên localhost | Báo cáo trung thực theo B5 của Như. Thêm S4 (1.000 bài) như một cách **trung thực** để nới khoảng cách. |
| Thất bại | Python client có GIL → ở concurrency 50, chính client là nút cổ chai | Dùng S3 để **so sánh tương đối** HIT với Không cache, ghi rõ trong mục "Giới hạn". k6 chạy bằng Docker là tùy chọn. |
| Thất bại | Bị nhiễu (Windows Defender, trình duyệt đang chạy) | Warm-up, ≥ 200 mẫu cho mỗi loại, báo median/p95 thay vì chỉ mean, ghi `env.json`. |
| Thất bại | Lock waiter gọi `GetById` đệ quy, chờ 50 ms mỗi vòng → p95 của S2 cao | Đây là hành vi đúng của thiết kế. Ghi nhận và giải thích, **không** sửa code của SV2. |
| Phạm vi | S4 phải seed thêm 900 bài → làm bẩn DB dùng để demo | S4 mặc định **tắt**. Nếu chạy thì khôi phục bằng `scripts/SeedPosts/restore_full_data.ps1` và ghi chú lại. |
| Phạm vi | Tự sửa tài liệu của Như/Quân để điền số | Cấm. Chỉ gửi tin nhắn kèm link (Phase 3). |
| An toàn | Script xóa nhầm key Redis | Chỉ `DEL` đúng `post:{id}` dựng bằng hàm `cache_key()`. Không bao giờ dùng `FLUSH*`, `KEYS`, `SCAN`+`DEL`. Có test khóa chặt điều này. |
| An toàn | Đếm `/api/cache/stats` bị lẫn lượt demo | Ghi lại stats trước và sau khi chạy, báo phần chênh lệch (delta), ghi chú đây là lượt đo. |

## 7. Validation gate (trả lời trước khi `/ak:cook`)

1. Máy đo là máy dùng để demo? → Nên đúng. Nếu khác máy thì ghi rõ trong `env.json` và báo cáo.
2. Số bài lúc đo bao nhiêu? → Ghi `totalItems` vào `env.json` (hiện ~101 hoặc theo bản đầy đủ SCRUM-32).
3. Có chạy S4 (1.000 bài) không? → Mặc định **không**. Chỉ chạy nếu còn thời gian và chấp nhận khôi phục DB.
4. Có cần k6 thật cho đúng tên ticket không? → Mặc định dùng tải đồng thời viết bằng Python. Nếu thầy đòi đúng tên công cụ thì dùng k6 qua `docker run grafana/k6`. Máy hiện **không có** `k6`/`ab`.

## 8. Định nghĩa "Xong"

- [ ] `python -m unittest` trong `scripts/Benchmark` xanh.
- [ ] Có một thư mục `results/<nhãn>` chính thức được commit, số trong báo cáo truy ngược được về file này.
- [ ] ≥ 4 biểu đồ PNG được nhúng trong chương báo cáo.
- [ ] S2 chứng minh được số MISS = 1 trên 50 request (hoặc giải thích được nếu khác).
- [ ] Đã nhắn Quân (mục 5 báo cáo) và Như (CSV Jira: 39/40/41/42 → Done; checklist Phần 4).
