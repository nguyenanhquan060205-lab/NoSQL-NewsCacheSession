---
phase: 5
title: "Automated Invalidation & Expiry Test Suite (SCRUM-23, SCRUM-35, SCRUM-37)"
status: completed
priority: P1
effort: "3h"
dependencies: ["phase-04-realtime-view-counter.md"]
ticket: ["SCRUM-23", "SCRUM-35", "SCRUM-37"]
---

# Phase 5: Automated Invalidation & Expiry Test Suite

> **Cam kết ranh giới file**: SV2 **chỉ viết test trong `tests/NewsCacheSession.Tests`**, TUYỆT ĐỐI KHÔNG sửa các method `GetAll`, `Create`, `Update`, `Delete` của SV1 trong `PostsController.cs`.

## 1. Mục Tiêu (Objective)
Giải quyết **SCRUM-23** (Xác thực Cache Invalidation), **SCRUM-35** (Test tự động Cache Invalidation) và **SCRUM-37** (Test tự động TTL và Session Expiry):
1. **Xác thực cơ chế Invalidation**:
   - Khi bài viết được sửa (`PUT`) hoặc xóa (`DELETE`), kiểm tra và khẳng định key `post:{id}` bị xóa khỏi Redis ngay lập tức (`DEL post:{id}`).
   - Kiểm tra `posts:ver` tăng 1 đơn vị qua `BumpListVersionAsync()` O(1).
2. **Kiểm thử tự động vòng đời Session (SCRUM-37)**:
   - Kiểm tra phiên hết hạn tự động khi TTL về 0.
   - Kiểm tra `SessionAuthMiddleware` thực hiện Sliding Expiration (gia hạn TTL 30 phút khi có request).
3. **Kiểm thử tự động Cache-Aside & Distributed Lock**:
   - Khẳng định 50 luồng đồng thời gọi `GetById` chỉ có 1 luồng truy vấn MongoDB.

---

## 2. Test Matrix (TDD Enforced)

| Test Case ID | File Test | Kịch Bản Kiểm Thử | Điều Kiện Pass |
|---|---|---|---|
| **TC-INVAL-01** | `CacheInvalidationTests.cs` | Cache bài viết đang có trong Redis -> Thực hiện cập nhật bài | Key `post:{id}` biến mất khỏi Redis; lần đọc tiếp theo gọi Mongo và nạp lại cache mới |
| **TC-INVAL-02** | `CacheInvalidationTests.cs` | Cache bài viết đang có trong Redis -> Thực hiện xóa bài viết | Key `post:{id}` biến mất khỏi Redis; `posts:ver` tăng thêm 1; gọi `GetById` trả 404 |
| **TC-EXPIRY-01** | `SessionExpiryTests.cs` | Tạo session với TTL ngắn 2 giây -> đợi 3 giây | Redis xóa key `session:{id}`, Middleware không tìm thấy session, API trả 401 |
| **TC-SLIDE-01** | `SessionExpiryTests.cs` | Tạo session TTL 30 phút -> gửi request qua Middleware | TTL của key `session:{id}` được gia hạn lại đủ 30 phút, `lastActive` được cập nhật |

---

## 3. Các Bước Triển Khai (Implementation Steps)

Tất cả các bước đều diễn ra trong thư mục `tests/NewsCacheSession.Tests/`:
1. Viết `CacheInvalidationTests.cs` (kiểm tra `DEL post:{id}` và `INCR posts:ver`).
2. Viết `SessionExpiryTests.cs` (kiểm tra TTL và Sliding Expiration).
3. Chạy toàn bộ test suite để nghiệm thu 100% tự động.

---

## 4. Lệnh Kiểm Tra & Nghiệm Thu (Verification Commands)

```bash
dotnet test --filter "FullyQualifiedName~CacheInvalidation"
dotnet test --filter "FullyQualifiedName~SessionExpiry"
```
