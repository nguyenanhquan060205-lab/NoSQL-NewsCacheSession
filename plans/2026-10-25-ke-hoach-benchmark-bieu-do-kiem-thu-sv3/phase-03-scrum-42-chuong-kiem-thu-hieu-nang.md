---
phase: 3
ticket: SCRUM-42
title: "Chương kiểm thử hiệu năng + bàn giao số liệu cho nhóm"
status: completed
priority: P1
effort: "2.5h"
dependsOn: [1, 2]
---

# Phase 03 — SCRUM-42: Chương kiểm thử hiệu năng

> Chế độ `--deep`: **scout lại trước khi viết**. Đọc `docs/bao-cao-nguyen-ly-cache-aside.md`
> (giọng văn, đánh số mục) và `docs/ĐỀ TÀI 06.docx` (yêu cầu phần thực nghiệm) để chương này
> ghép vào báo cáo chung không bị lệch.

## File
- `docs/bao-cao-kiem-thu-hieu-nang.md` (mới, SV3)
- `docs/assets/kiem-thu-hieu-nang/*.png` (chép từ `results/…-chinh-thuc/charts/`)

## Dàn ý
1. **Mục tiêu kiểm thử.** Trả lời ba câu hỏi: lần 1 vs lần 2 nhanh hơn bao nhiêu, khóa có chặn được stampede không, chịu tải được bao nhiêu.
2. **Môi trường.** Bảng lấy từ `env.json`: CPU/RAM/OS, bản Docker, MongoDB/Redis chạy cùng máy, số bài, commit đo.
3. **Phương pháp.**
   - Ba đường đọc (Không cache / MISS / HIT) và vì sao chọn `/slug` làm mốc.
   - Keep-alive, warm-up, 200 mẫu cho mỗi loại, kiểm chứng `X-Cache` cho từng mẫu.
   - Vì sao **bỏ** cách đo bằng `curl.exe` cũ: mỗi lần là một tiến trình mới và một bắt tay TCP mới.
4. **Kết quả.**
   - 4.1 Độ trễ: bảng (`summary.md`) + biểu đồ 1–3.
   - 4.2 Stampede: x/50 MISS + biểu đồ 5.
   - 4.3 Tải đồng thời: biểu đồ 4.
   - *(4.4 nếu có)* 1.000 bài.
5. **Phân tích.**
   - Vì sao MISS chậm hơn Không cache: 7 bước của Cache-Aside (theo B5 của Như).
   - Vì sao không ra "200 ms vs 5 ms": cùng máy, dữ liệu nhỏ, có index, sàn chi phí HTTP.
   - Ý nghĩa của p95/p99. Dùng lại tỉ lệ thống kê hit/miss từ `/api/cache/stats`.
6. **Giới hạn của phép đo.** Client Python bị GIL, đo trên một máy, Windows gây nhiễu, cache nóng của MongoDB (WiredTiger).
7. **Kết luận** + liên hệ ngược về barem (Phần 4).
8. **Cách tái hiện.** Đúng ba lệnh: `benchmark.py` → `plot.py` → mở `summary.md`.

**Quy tắc:** mọi con số trong chương phải tra ngược được về `results/…-chinh-thuc/summary.json`.
Không làm tròn quá 2 chữ số thập phân, không chọn lọc lượt đo đẹp.

## Các bước
1. [ ] Nhánh `SCRUM-42-viet-chuong-kiem-thu-hieu-nang` tách từ nhánh SCRUM-41.
2. [ ] Viết chương theo dàn ý, nhúng ảnh bằng đường dẫn tương đối.
3. [ ] Tự đối chiếu: so từng con số trong chương với `summary.json`.
4. [ ] Commit `docs(SCRUM-42): chương kiểm thử hiệu năng`.
5. [ ] **Bàn giao (nhắn tin, không sửa file người khác):**
   - Quân (SV2): mục 5 báo cáo đang ghi "Lần 1 (MISS) ~80ms - 200ms" — số đo thật là 8,57 ms
     (trung vị). Nhờ Quân sửa bằng số từ chương này (gửi link).
   - Như (SV1): cập nhật `nosql-jira-tasks.csv` (SCRUM-39/40/41/42 → Done) và Phần 4 của
     `checklist-barem.md`. Gợi ý cập nhật bảng B4 trong `kich-ban-demo-va-do-hieu-nang.md`.
     Thêm: `bao-cao-tien-do.md` dòng 289–290 và `ra-soat-cai-dat-tu-dau.md` dòng 227 (tick việc SV3).
   - Cả nhóm: mục 11.5 `huong_dan_nhom.md` (file chung) còn script benchmark mẫu cũ.
6. [ ] Hỏi user trước khi `git push` / mở PR.

## Tiêu chí đạt
- Chương có đủ 8 mục, ≥ 4 hình, mọi số đều truy ngược được.
- SCRUM-44 (slide) dùng lại được biểu đồ 1 + bảng 4.1 mà không phải làm lại.
