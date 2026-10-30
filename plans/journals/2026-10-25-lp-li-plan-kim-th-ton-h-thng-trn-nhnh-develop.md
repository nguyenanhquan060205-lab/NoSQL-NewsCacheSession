---
title: Lập lại plan kiểm thử toàn hệ thống trên nhánh develop
date: 2026-10-25
summary: "Plan 6 phase, môi trường QA tách biệt, phương án B sửa file người khác, phát hiện main hỏng build test"
---

# Lập lại plan kiểm thử toàn hệ thống trên nhánh develop

# Lập lại plan kiểm thử toàn hệ thống trên nhánh develop

## Chuyện gì đã xảy ra
- Plan cũ `261025-1436-...` không còn trên đĩa nên lập lại từ đầu: `plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/`.
- Đọc lại đề 06, CSV Jira, toàn bộ backend, frontend, script. Chạy baseline: .NET 27/27, Vitest 103/103,
  oxlint sạch; 2 test SeedRedis fail, SeedPosts thiếu `pymongo`.
- Phát hiện `main` trên GitHub không build được project test: test gọi constructor `PostsController`
  3 tham số trong khi SCRUM-39 đã đổi thành 5. Bản sửa lượt xem chưa commit tình cờ vá luôn chỗ này.
- Key `posts:dirty_views` không có trong `docs/redis-keyspace.md` — rủi ro khi thầy đối chiếu doc với RedisInsight.
- API đang chạy là bản 23/10, chỉ đúng DB nhờ biến môi trường; Mongo Homebrew chiếm 27017.

## Quyết định
- Tạo nhánh `develop`, commit `9665335` (bản sửa lượt xem + vá build test). Mọi việc làm trên `develop`, cuối Phase 5 mới PR lên `main`.
- Phương án B: lỗi chặn demo/barem trong file của Như/Định thì xin phép nhóm rồi sửa.
- Lỗi Redis sập sửa luôn, không hoãn. Deploy sau cùng: Render + Atlas M0 + Redis Cloud free + Vercel.
- QA dùng container riêng (27019/6380), API 5135, Vite 3001 — không đụng stack demo.

## Bước tiếp theo
- `/ak-debug` Phase 1 → 2 → 3/4, sửa ở Phase 5, deploy ở Phase 6.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
