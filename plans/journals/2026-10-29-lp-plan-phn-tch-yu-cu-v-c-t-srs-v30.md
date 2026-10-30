---
title: Lập plan phân tích yêu cầu và đặc tả SRS v3.0
date: 2026-10-29
summary: SRS v2.0 chưa commit lệch code 23 chỗ; plan 4 phase viết checker tài liệu trước rồi mới viết lại SRS
---

# Lập plan phân tích yêu cầu và đặc tả SRS v3.0

## What happened

- Lập plan `plans/261029-0425-phan-tich-yeu-cau-va-dac-ta-srs/` (`--deep --tdd`) từ `docs/ĐỀ TÀI 06.docx`
  và `docs/nosql-jira-tasks.csv`.
- `docs/SRS.md` v2.0 chưa commit, tự nhận "đồng bộ 100% với mã nguồn". Đối chiếu với code thì sai 23 chỗ
  (D1–D23 trong `reports/00-scout-doi-chieu-tai-lieu-voi-code.md`). Mấy chỗ làm hỏng demo:
  - cookie `news_session`, code thật là `SessionId` (`Services/CurrentUserService.cs:17`);
  - RedisInsight cổng 8001, thật là 5540 (`docker-compose.yml:30`);
  - `/api/cache/stats` sai hết tên field, thật là `hits, misses, totalRequests, hitRate`;
  - ghi "49/49 Jira", CSV chỉ có 37 ticket và 11 ticket chưa Done;
  - demo hứa MISS ~150–200 ms, số đo thật 8,74 ms.
- SRS v2.0 còn tự chia điểm con cho phần 2 và phần 3 của barem, đề bài không có (D24).
- Đọc docx bằng `zipfile` + regex ra 26 đoạn. Đã kiểm 19 câu trích DB-01…DB-19: khớp hết, phủ đủ mọi đoạn có yêu cầu.
- Đã kiểm 44 tham chiếu `File.cs::Method` cho danh mục test case: tất cả có thật. Đếm được 21 endpoint từ code.

## Decision

- Quân chọn: viết đè `docs/SRS.md` thành v3.0, chụp v2.0 trước. Giữ ID FR-01…FR-21.
- Bộ kiểm thử tài liệu đặt ở `scripts/DocCheck/` (thư mục mới của Quân), chỉ dùng thư viện chuẩn + `unittest`
  vì máy không có `pytest`. Gồm 12 phép kiểm C1–C12. Bỏ qua "Lịch sử phiên bản" và "Phụ lục F" để chỗ ghi lỗi cũ không làm checker đỏ.
- Kiểm thử sống làm cả hai nơi:
  - local: thao tác ghi và `MONITOR` chỉ trên QA 27019/6380, stack demo chỉ đọc;
  - bản deploy: chỉ GET, dưới 20 request, không đăng nhập.
- Red-team inline có 5 phát hiện được áp dụng: tách DB-18/DB-19, DB-03 vào NFR-09, C4 bắt nhãn mermaid,
  dùng `docker exec … redis-cli` vì máy không có `redis-cli`, làm rõ C9.
- Tự sửa một lỗi trong plan: "~2.000 bài" là sức chứa Redis Cloud chứ không phải số bài.
  Atlas lúc deploy có 10.000 bài chưa xóa (`reports/06-deploy.md:7`).

## Next steps

- Chạy `/ak:cook plans/261029-0425-phan-tich-yeu-cau-va-dac-ta-srs/plan.md`, bắt đầu từ Phase 1.
- Docker Desktop đang tắt, phải bật trước Phase 4.
- Sau Phase 4: gửi `reports/04-thong-bao-chu-so-huu.md` cho SV1, SV3 và cả nhóm.
  Ba chỗ lạc hậu: `AGENTS.md` §6, `docs/checklist-barem.md`, trạng thái CSV.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
