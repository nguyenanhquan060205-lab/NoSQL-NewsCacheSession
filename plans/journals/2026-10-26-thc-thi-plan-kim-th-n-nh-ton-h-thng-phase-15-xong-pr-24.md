---
title: "Thực thi plan kiểm thử ổn định toàn hệ thống — Phase 1–5 xong, PR #24"
date: 2026-10-26
summary: "Test thật tìm ra Redis sập làm treo 6s rồi 500, 10/10 đăng ký song song thành admin; 74/74 integration xanh sau sửa, demo diễn tập 2 lượt đạt"
---

# Thực thi plan kiểm thử ổn định toàn hệ thống — Phase 1–5 xong, PR #24

## Chuyện gì đã xảy ra
- Dựng stack QA tách biệt (Mongo :27019, Redis :6380 không lưu đĩa, API :5135, Vite :3001 bằng config ngoài repo). Baseline xanh; G5 (2 test SeedRedis fail) hóa ra do Python hệ thống thiếu `bson`.
- Viết 45 integration test qua `WebApplicationFactory<HealthController>` (không phải sửa Program.cs), chặn cứng DB `newsdb_it_*` + Redis DB 15, mặc định Skipped. 7 test đỏ đúng giả thuyết: 9/10 request tạo bài cùng tiêu đề trả 500; 10/10 đăng ký song song thành admin; cookie không trượt; TTL hardcode; không giới hạn độ dài.
- Đo độ bền: Redis sập làm MỌI request (kể cả bài đã cache) treo ~6s rồi 500 — StackExchange.Redis xếp lệnh vào backlog chờ hết syncTimeout 5s. Chỉ bắt exception là không đủ (GetAll sẽ treo ~15s). Lock kẹt: 96 vòng đệ quy, 5,04s. Mongo sập: bài đã cache vẫn HIT, phần còn lại treo 30s. Tải 15 phút: 9,47 triệu request, 0 lỗi, RSS đi ngang.
- Sửa SV2 (6 commit), rồi các mục của Như/Định sau khi nhóm đồng ý (10 commit). Kết quả: 74/74 integration, E2E 12/12, diễn tập 3 bước × 2 lượt trên stack demo chạy develop, README chạy đúng như viết (trả 27017 cho container).

## Quyết định
- Kiểm `IsConnected` trước mỗi lệnh Redis (RedisAvailability) để báo lỗi tức thì; đọc cache lỗi = MISS, thao tác cần phiên = 503. Middleware 503 đăng ký trong `UseSessionAuth()` nên không đụng Program.cs.
- Admin đầu tiên chốt bằng insert `{_id:"bootstrapAdmin"}` vào `meta`. Review sau đó tìm ra lỗ hổng (giành quyền xong mà thua insert → không ai làm admin được) — test race đỏ 4/10 với điều kiện "chưa có user", đổi thành "chưa có admin" thì 0/10.
- Doc ghi lock giải phóng bằng Lua — MONITOR cho thấy thực tế là WATCH/GET/MULTI/UNLINK/EXEC; sửa doc và tên test theo bằng chứng.

## Bài học
- Test "xanh" của mock gọi mock không chứng minh gì; test qua HTTP thật mới lộ lỗi chen nhau.
- Đo trước khi thiết kế bản sửa: số đo 6s/backlog đổi hẳn cách sửa S1.
- bash 3.2 của macOS và zsh (không tách từ `$VAR`) gây hai lỗi script kiểm thử — viết script đo bằng Python.

## Việc tiếp theo
- Nhóm review + merge PR #24.
- Phase 6: Quân tạo tài khoản Atlas/Redis Cloud/Render/Vercel theo `docs/huong-dan-deploy.md`, gửi URL Render để commit `src/frontend/vercel.json` và chạy smoke test production; đo cold start.
- Seed lại Redis demo ngay trước buổi chấm; Định diễn tập có RedisInsight + quay video (SCRUM-45).
- Báo nhóm: hai file CLAUDE.md còn mô tả lock cũ.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
