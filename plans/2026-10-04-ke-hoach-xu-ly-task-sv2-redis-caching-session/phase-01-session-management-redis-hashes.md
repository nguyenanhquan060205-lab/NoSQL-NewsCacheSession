---
phase: 1
title: "Session Management & Authentication Pipeline (Redis Hashes + Sliding TTL)"
status: completed
priority: P1
effort: "3h"
dependencies: ["phase-00-test-infrastructure-setup.md"]
ticket: ["SCRUM-14", "SCRUM-15"]
---

# Phase 1: Session Management & Authentication Pipeline

## 1. Mục Tiêu (Objective)
Giải quyết dứt điểm 2 task **SCRUM-14** (Lưu session bằng Redis Hashes + EXPIRE) và **SCRUM-15** (Middleware xác thực + sliding expiration):
1. **Khắc phục lỗ hổng `CreateSessionAsync`**: Thêm `role` vào tham số `CreateSessionAsync`, lưu đầy đủ 5 trường vào Redis Hash: `userId`, `username`, `role`, `loginAt`, `lastActive`.
2. **Cấu hình TTL tập trung**: Đọc TTL từ `appsettings.json` (`SessionSettings:TtlMinutes`, mặc định 30 phút), không hardcode trong mã nguồn.
3. **Hiện thực hoàn chỉnh `SessionAuthMiddleware.cs`**:
   - Trích xuất `SessionId` từ Cookie hoặc Header.
   - Tra cứu `HGETALL session:{sessionId}`.
   - Gán đầy đủ `HttpContext.Items["UserId"]`, `["Username"]`, `["Role"]`, `["LoginAt"]`.
   - **Thực hiện Sliding Expiration**: Gia hạn TTL thêm 30 phút (`EXPIRE session:{sessionId} 1800`) và cập nhật `lastActive` qua `HSET`.

---

## 2. Test Matrix (TDD Enforced)

Viết file test `tests/NewsCacheSession.Tests/Services/SessionServiceTests.cs` và `tests/NewsCacheSession.Tests/Middleware/SessionAuthMiddlewareTests.cs` trước khi implement code.

| Test Case ID | Loại | Mô Tả Kịch Bản | Điều Kiện Pass (Assertion) |
|---|---|---|---|
| **TC-SESS-01** | Unit | `CreateSessionAsync` với đủ 5 fields | `HashSetAsync` được gọi với đúng 5 `HashEntry` (`userId`, `username`, `role`, `loginAt`, `lastActive`), `KeyExpireAsync` được gọi với `ttl` |
| **TC-SESS-02** | Unit | `GetSessionAsync` khi session hợp lệ | Trả về `Dictionary<string, string>` có chứa `role`, `userId`, `username` |
| **TC-SESS-03** | Unit | `RefreshSessionAsync` | `KeyExpireAsync` được gọi đúng key `session:{sessionId}` với TTL mới |
| **TC-SESS-04** | Unit | `RemoveSessionAsync` khi logout | `KeyDeleteAsync` được gọi đúng key `session:{sessionId}` |
| **TC-MID-01** | Middleware | Request có Cookie `SessionId` hợp lệ | `context.Items["UserId"]` == userId, `context.Items["Role"]` == role, gọi `KeyExpireAsync` và `HashSetAsync` cập nhật `lastActive` |
| **TC-MID-02** | Middleware | Request có Header `X-Session-Id` hợp lệ | Cư xử hoàn toàn tương đương Cookie (phục vụ Swagger/Postman) |
| **TC-MID-03** | Middleware | Request không có session hoặc session không tồn tại trên Redis | Không gán `context.Items`, `_next(context)` vẫn được gọi, không throw exception |

---

## 3. Các Bước Triển Khai (Implementation Steps)

### Bước 1 (TDD Red): Viết Test Trước
Tạo `SessionServiceTests.cs` và `SessionAuthMiddlewareTests.cs` trong `NewsCacheSession.Tests`. Chạy `dotnet test` -> Kết quả ĐỎ (Fail).

### Bước 2: Nâng cấp `ISessionService` & `RedisSessionService`
- File: `src/NewsCacheSession.Api/Services/ISessionService.cs`
- File: `src/NewsCacheSession.Api/Services/RedisSessionService.cs`
```csharp
public async Task CreateSessionAsync(string sessionId, string userId, string username, string role, TimeSpan ttl)
{
    var key = Key(sessionId);
    var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString();
    var entries = new HashEntry[]
    {
        new("userId", userId),
        new("username", username),
        new("role", role),
        new("loginAt", now),
        new("lastActive", now)
    };
    await _db.HashSetAsync(key, entries);
    await _db.KeyExpireAsync(key, ttl);
}

// Giữ overload cũ để đảm bảo không làm vỡ code nếu nơi khác chưa truyền role
public Task CreateSessionAsync(string sessionId, string userId, string username, TimeSpan ttl) =>
    CreateSessionAsync(sessionId, userId, username, "user", ttl);
```

### Bước 3: Bổ sung cấu hình `appsettings.json`
- File: `src/NewsCacheSession.Api/appsettings.json`
```json
"SessionSettings": {
  "TtlMinutes": 30
}
```

### Bước 4: Triển khai `SessionAuthMiddleware.cs`
- File: `src/NewsCacheSession.Api/Middleware/SessionAuthMiddleware.cs`
```csharp
public async Task InvokeAsync(HttpContext context, ISessionService sessionService, IConfiguration config)
{
    var sessionId = context.Request.Cookies["SessionId"]
                 ?? context.Request.Headers["X-Session-Id"].FirstOrDefault();

    if (!string.IsNullOrEmpty(sessionId))
    {
        var session = await sessionService.GetSessionAsync(sessionId);
        if (session != null && session.TryGetValue("userId", out var userId))
        {
            context.Items["UserId"] = userId;
            context.Items["Username"] = session.GetValueOrDefault("username", string.Empty);
            context.Items["Role"] = session.GetValueOrDefault("role", "user");
            context.Items["LoginAt"] = session.GetValueOrDefault("loginAt", string.Empty);

            var ttlMinutes = config.GetValue<int>("SessionSettings:TtlMinutes", 30);
            var ttl = TimeSpan.FromMinutes(ttlMinutes);

            // Sliding Expiration: Gia hạn TTL phiên
            await sessionService.RefreshSessionAsync(sessionId, ttl);
        }
    }

    await _next(context);
}
```

### Bước 5 (TDD Green): Chạy lại test suite
Chạy `dotnet test` -> Kết quả XANH (Pass).

---

## 4. Lệnh Kiểm Tra & Nghiệm Thu (Verification Commands)

```bash
# 1. Chạy unit tests tự động
dotnet test --filter "FullyQualifiedName~Session"

# 2. Kiểm tra trực tiếp trên container Redis
docker exec -it nosql-redis redis-cli HGETALL "session:<sessionId>"
docker exec -it nosql-redis redis-cli TTL "session:<sessionId>"
```
