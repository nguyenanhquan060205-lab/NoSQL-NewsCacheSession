---
phase: 6
title: "Báo Cáo Chuyên Đề: Nguyên Lý Cache-Aside Pattern (SCRUM-28)"
status: completed
priority: P2
effort: "2h"
dependencies: ["phase-05-cache-invalidation-and-testing.md"]
ticket: ["SCRUM-28"]
---

# Phase 6: Báo Cáo Chuyên Đề Cache-Aside Pattern

## 1. Mục Tiêu (Objective)
Giải quyết **SCRUM-28** (Viết chương nguyên lý Cache-Aside Pattern trong báo cáo đồ án NoSQL):
1. Soạn thảo tài liệu chuẩn học thuật cho báo cáo Word / Markdown về nguyên lý Cache-Aside Pattern.
2. Vẽ sơ đồ luồng dữ liệu (Sequence Diagram & Flowchart) khi Cache Hit và Cache Miss.
3. Phân tích hiện tượng Cache Stampede (Dog-piling effect) và cơ chế giải quyết bằng Distributed Lock (`SET NX PX`).
4. Phân tích bài toán tính nhất quán dữ liệu (Cache Consistency) và lý do tại sao phải **Ghi DB trước, Xóa Cache sau**.

---

## 2. Cấu Trúc Nội Dung Báo Cáo

1. **Tổng quan về Caching trong kiến trúc NoSQL**:
   - Vị trí của Redis trong hệ thống (In-memory datastore).
   - So sánh các chiến lược Caching: Cache-Aside (Lazy Loading), Write-Through, Write-Behind, Refresh-Ahead.
2. **Cơ chế hoạt động của Cache-Aside**:
   - Luồng đọc: Cache check -> Hit / Miss -> Fetch DB -> Cache population -> Return.
   - Luồng cập nhật / xóa: Write DB -> Invalidate Cache (DEL).
3. **Các thách thức & giải pháp kỹ thuật đã áp dụng trong đề tài**:
   - **Cache Stampede**: Giải quyết bằng distributed lock `lock:post:{id}` với TTL 5s và double-check idiom.
   - **Cache Penetration**: Ngăn chặn bằng cách xử lý bài viết không tồn tại.
   - **List Cache Invalidation**: Giải quyết bài toán tốn kém O(N) của `SCAN` bằng cơ chế số phiên bản `posts:ver` O(1).
   - **Realtime Counters**: Phân tách luồng đọc ghi với atomic counter `INCR post:{id}:views` và Write-behind sync.

---

## 3. Lệnh Kiểm Tra & Nghiệm Thu (Verification Commands)

- File báo cáo hoàn thành đặt tại: `docs/bao-cao-nguyen-ly-cache-aside.md`.
