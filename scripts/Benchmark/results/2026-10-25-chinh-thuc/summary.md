# Kết quả đo hiệu năng

Đo ngày 2026-10-25 · 200 mẫu mỗi loại · 10.150 bài viết trong MongoDB · API, MongoDB, Redis cùng một máy

## Độ trễ tuần tự (ms)

| Loại | n | Trung bình | Trung vị | p95 | p99 | Nhỏ nhất | Lớn nhất |
|---|---|---|---|---|---|---|---|
| Không cache (MongoDB) | 200 | 3,66 | 3,59 | 4,46 | 4,63 | 2,88 | 4,89 |
| Cache MISS (MongoDB → Redis) | 200 | 8,74 | 8,57 | 10,42 | 10,90 | 7,31 | 12,19 |
| Cache HIT (Redis) | 200 | 2,96 | 2,92 | 3,55 | 3,82 | 2,31 | 4,06 |

Theo trung vị: Cache MISS chậm hơn Cache HIT **2,93 lần**; Không cache chậm hơn Cache HIT **1,23 lần**.

## Cache stampede

| Lần | Request đồng thời | MISS (đọc MongoDB) | HIT | Lỗi | p95 (ms) |
|---|---|---|---|---|---|
| 1 | 50 | 1/50 | 49 | 0 | 57,98 |
| 2 | 50 | 1/50 | 49 | 0 | 104,26 |
| 3 | 50 | 1/50 | 49 | 0 | 104,61 |
| 4 | 50 | 1/50 | 49 | 0 | 59,51 |
| 5 | 50 | 1/50 | 49 | 0 | 115,10 |

## Tải đồng thời

| Loại | Luồng | Request | Lỗi | Request/giây | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|---|---|---|
| Cache HIT (Redis) | 1 | 500 | 0 | 328,1 | 2,98 | 3,72 | 4,23 |
| Không cache (MongoDB) | 1 | 500 | 0 | 279,0 | 3,55 | 4,29 | 4,71 |
| Cache HIT (Redis) | 10 | 500 | 0 | 889,4 | 10,39 | 16,38 | 24,22 |
| Không cache (MongoDB) | 10 | 500 | 0 | 875,5 | 10,97 | 15,47 | 16,99 |
| Cache HIT (Redis) | 50 | 500 | 0 | 885,6 | 51,07 | 87,25 | 106,81 |
| Không cache (MongoDB) | 50 | 500 | 0 | 762,5 | 59,59 | 98,87 | 116,10 |
