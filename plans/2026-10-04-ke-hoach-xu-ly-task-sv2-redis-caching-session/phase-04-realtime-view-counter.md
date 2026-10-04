---
phase: 4
title: "Realtime View Counter & Write-Behind Sync Worker (INCR post:{id}:views)"
status: completed
priority: P1
effort: "2h"
dependencies: ["phase-03-cache-aside-stampede-lock.md"]
ticket: ["SCRUM-25"]
---

# Phase 4: Realtime View Counter & Write-Behind Sync Worker

## 1. Mục Tiêu (Objective)
Giải quyết **SCRUM-25** (Bộ đếm lượt xem realtime bằng `INCR` + job flush về MongoDB):
1. Hoàn thiện method `IncrementView(string id)` trong `PostsController.cs` dùng atomic command `INCR post:{id}:views` (không TTL).
2. Áp dụng kỹ thuật **Write-Behind Pattern** và **Dirty Tracking**: Khi view tăng, thêm ID bài viết vào Redis Set `posts:dirty_views` để worker đồng bộ có mục tiêu rõ ràng mà không cần chạy `SCAN` tốn kém.
3. Xây dựng Background Service `ViewCountSyncWorker : BackgroundService` định kỳ (mỗi 1-2 phút) quét các ID trong `posts:dirty_views`, đọc số view trên Redis và cập nhật về field `views` của collection `posts` trong MongoDB.

---

## 2. Test Matrix (TDD Enforced)

Viết test suite trong `tests/NewsCacheSession.Tests/Services/ViewCountSyncTests.cs`:

| Test Case ID | Loại | Mô Tả Kịch Bản | Điều Kiện Pass (Assertion) |
|---|---|---|---|
| **TC-VIEW-01** | Unit | Gọi `IncrementView` lần đầu cho post | Key `post:{id}:views` = 1, `posts:dirty_views` chứa `id`, trả về `{ views: 1 }` |
| **TC-VIEW-02** | Concurrency | 100 request gọi `IncrementView` đồng thời | Giá trị cuối cùng trên Redis đúng chính xác 100, không bị mất mát dữ liệu |
| **TC-SYNC-01** | Background | Worker thực hiện chu kỳ flush | Field `views` của Post trong MongoDB được update bằng số view trên Redis, `posts:dirty_views` được dọn sạch |

---

## 3. Các Bước Triển Khai (Implementation Steps)

### Bước 1: Method `IncrementView` trong `PostsController.cs`
```csharp
[HttpPost("{id}/view")]
public async Task<IActionResult> IncrementView(string id)
{
    if (!ObjectId.TryParse(id, out _))
        return BadRequest(new { message = "ID bài viết không hợp lệ." });

    var viewsKey = ViewsKey(id);
    var newViews = await _cacheService.IncrementAsync(viewsKey);

    // Đánh dấu dirty để worker đồng bộ về MongoDB (Write-Behind)
    await _cacheService.MarkDirtyViewAsync(id);

    return Ok(new { views = newViews });
}
```

### Bước 2: Tạo Worker `Services/ViewCountSyncWorker.cs`
```csharp
public class ViewCountSyncWorker : BackgroundService
{
    private readonly IServiceProvider _services;
    private readonly ILogger<ViewCountSyncWorker> _logger;

    public ViewCountSyncWorker(IServiceProvider services, ILogger<ViewCountSyncWorker> logger)
    {
        _services = services;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
            await FlushViewsToMongoAsync(stoppingToken);
        }
    }

    public async Task FlushViewsToMongoAsync(CancellationToken ct)
    {
        using var scope = _services.CreateScope();
        var cache = scope.ServiceProvider.GetRequiredService<ICacheService>();
        var mongo = scope.ServiceProvider.GetRequiredService<MongoContext>();

        var dirtyPostIds = await cache.GetAndClearDirtyViewsAsync();
        foreach (var postId in dirtyPostIds)
        {
            var viewsStr = await cache.GetAsync($"post:{postId}:views");
            if (long.TryParse(viewsStr, out var views))
            {
                await mongo.Posts.UpdateOneAsync(
                    p => p.Id == postId,
                    Builders<Post>.Update.Set(p => p.Views, views),
                    cancellationToken: ct);
            }
        }
    }
}
```

### Bước 3: Đăng ký Worker trong `Program.cs`
```csharp
builder.Services.AddHostedService<ViewCountSyncWorker>();
```

---

## 4. Lệnh Kiểm Tra & Nghiệm Thu (Verification Commands)

```bash
dotnet test --filter "FullyQualifiedName~ViewCountSync"

# Test tăng view
curl -X POST http://localhost:5000/api/posts/<postId>/view
docker exec -it nosql-redis redis-cli GET "post:<postId>:views"
```
