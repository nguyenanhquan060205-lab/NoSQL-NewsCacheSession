---
phase: 2
title: "Cache Service Wrapper, Distributed Lock & Metrics (ICacheService, RedisCacheService, Stats)"
status: completed
priority: P1
effort: "2h"
dependencies: ["phase-01-session-management-redis-hashes.md"]
ticket: ["SCRUM-20", "SCRUM-24", "SCRUM-34"]
---

# Phase 2: Cache Service Wrapper, Distributed Lock & Metrics

## 1. Mục Tiêu (Objective)
Giải quyết **SCRUM-20** (Wrapper cache client + hook đo metrics), chuẩn bị hạ tầng khóa cho **SCRUM-24** (Distributed Lock) và **SCRUM-34** (Endpoint `/cache/stats`):
1. Bổ sung các phương thức khóa phân tán vào `ICacheService`:
   - `Task<bool> AcquireLockAsync(string key, string value, TimeSpan expiry)` (`SET NX PX`)
   - `Task<bool> ReleaseLockAsync(string key, string value)` (Lua script an toàn)
2. Tích hợp bộ đếm Metrics (Cache Hits, Cache Misses, Total Requests) để đo hiệu năng.
3. Tạo `CacheStatsController` với endpoint `GET /api/cache/stats` trả về tỷ lệ Hit Rate (%) phục vụ demo và báo cáo.

---

## 2. Test Matrix (TDD Enforced)

| Test Case ID | Loại | Mô Tả Kịch Bản | Kết Quả Mong Đợi |
|---|---|---|---|
| **TC-CACHE-01** | Unit | Gọi `SetAsync` và `GetAsync` | Lưu và đọc chuỗi đúng giá trị, TTL được thiết lập |
| **TC-CACHE-02** | Unit | Đọc key không tồn tại | Trả về null, counter Misses tăng 1 |
| **TC-CACHE-03** | Unit | Đọc key tồn tại | Trả về value, counter Hits tăng 1 |
| **TC-LOCK-01** | Unit | `AcquireLockAsync` lần đầu | Trả về `true`, key lock xuất hiện trên Redis với TTL 5s |
| **TC-LOCK-02** | Unit | `AcquireLockAsync` lần hai khi lock chưa hết hạn | Trả về `false` (không thể tranh chấp) |
| **TC-LOCK-03** | Unit | `ReleaseLockAsync` với đúng token owner | Lock được giải phóng, trả về `true` |
| **TC-LOCK-04** | Unit | `ReleaseLockAsync` với sai token owner | Không xóa lock của người khác, trả về `false` |
| **TC-STATS-01** | API | Gọi `GET /api/cache/stats` | Trả về JSON `{ hits, misses, totalRequests, hitRate }` |

---

## 3. Các Bước Triển Khai (Implementation Steps)

### Bước 1: Nâng cấp `ICacheService` & `RedisCacheService`
- File: `src/NewsCacheSession.Api/Services/ICacheService.cs`
- File: `src/NewsCacheSession.Api/Services/RedisCacheService.cs`

```csharp
public interface ICacheService
{
    Task<string?> GetAsync(string key);
    Task SetAsync(string key, string value, TimeSpan ttl);
    Task RemoveAsync(string key);
    Task<long> IncrementAsync(string key);

    // Distributed Lock primitives (SCRUM-24)
    Task<bool> AcquireLockAsync(string key, string value, TimeSpan expiry);
    Task<bool> ReleaseLockAsync(string key, string value);

    // Metrics (SCRUM-20, SCRUM-34)
    CacheStats GetStats();
}
```

Triển khai khóa bằng Lua Script:
```csharp
public async Task<bool> AcquireLockAsync(string key, string value, TimeSpan expiry) =>
    await _db.StringSetAsync(key, value, expiry, When.NotExists);

public async Task<bool> ReleaseLockAsync(string key, string value)
{
    const string script = @"
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end";
    var result = await _db.ScriptEvaluateAsync(script, new RedisKey[] { key }, new RedisValue[] { value });
    return (int)result == 1;
}
```

### Bước 2: Tạo `Controllers/CacheStatsController.cs`
```csharp
[ApiController]
[Route("api/cache")]
public class CacheStatsController : ControllerBase
{
    private readonly ICacheService _cache;
    public CacheStatsController(ICacheService cache) => _cache = cache;

    [HttpGet("stats")]
    public IActionResult GetStats() => Ok(_cache.GetStats());
}
```

---

## 4. Lệnh Kiểm Tra & Nghiệm Thu (Verification Commands)

```bash
dotnet test --filter "FullyQualifiedName~CacheService"
curl http://localhost:5000/api/cache/stats
```
