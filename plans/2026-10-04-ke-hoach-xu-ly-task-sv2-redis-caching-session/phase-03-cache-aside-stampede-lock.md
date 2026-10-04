---
phase: 3
title: "Cache-Aside Engine & Anti-Stampede Lock (GET /api/posts/{id})"
status: completed
priority: P1
effort: "3h"
dependencies: ["phase-02-cache-client-and-metrics.md"]
ticket: ["SCRUM-21", "SCRUM-24"]
---

# Phase 3: Cache-Aside Engine & Anti-Stampede Lock

## 1. Mục Tiêu (Objective)
Giải quyết **SCRUM-21** (Hiện thực luồng Cache-Aside cho đọc bài viết) và **SCRUM-24** (Cơ chế khóa chống cache stampede `SET NX PX`):
1. Thay thế `throw new NotImplementedException();` trong `PostsController.GetById(string id)`.
2. Đính kèm header `X-Cache: HIT` hoặc `X-Cache: MISS` (phục vụ frontend badge SCRUM-38 và demo thầy chấm 2.5 điểm Cache-Aside).
3. Sử dụng Distributed Lock qua `_cacheService.AcquireLockAsync` (`lock:post:{id}`) ngăn chặn Cache Stampede.
4. Ghi đè `PostResponse.Views` bằng giá trị realtime từ `post:{id}:views` nếu key tồn tại (theo quy định tại Mục 6 của `AGENTS.md`).

---

## 2. Test Matrix (TDD Enforced)

Viết test suite trong `tests/NewsCacheSession.Tests/Controllers/PostsControllerCacheAsideTests.cs`:

| Test Case ID | Loại | Mô Tả Kịch Bản | Điều Kiện Pass (Assertion) |
|---|---|---|---|
| **TC-ASIDE-01** | Integration | Gọi `GET /api/posts/{id}` khi chưa cache (MISS) | Response 200 OK, Header `X-Cache` = "MISS", dữ liệu khớp MongoDB, Redis sinh key `post:{id}` có TTL 10 phút |
| **TC-ASIDE-02** | Integration | Gọi `GET /api/posts/{id}` lần thứ hai (HIT) | Response 200 OK, Header `X-Cache` = "HIT", không query MongoDB |
| **TC-ASIDE-03** | Integration | Có key `post:{id}:views` = 99 trong Redis | Response `Views` trả về đúng 99 (ghi đè views trong Mongo) |
| **TC-STAMP-01** | Concurrency | 50 luồng đồng thời gọi `GET /api/posts/{id}` khi cache MISS | Chỉ duy nhất 1 luồng gọi Mongo nạp cache; 49 luồng chờ và nhận `X-Cache: HIT` |
| **TC-ASIDE-04** | Edge | Bài viết bị xóa mềm (`isDeleted = true`) hoặc id không hợp lệ | Trả về 404 hoặc 400, không cache vào Redis |

---

## 3. Triển Khai Code Trong `PostsController.cs` (Method `GetById`)

```csharp
[HttpGet("{id}")]
public async Task<IActionResult> GetById(string id)
{
    if (!ObjectId.TryParse(id, out _))
        return BadRequest(new { message = "ID bài viết không hợp lệ." });

    var cacheKey = CacheKey(id);
    var viewsKey = ViewsKey(id);
    var lockKey = $"lock:{cacheKey}";

    // 1. Thử đọc từ Redis Cache
    var cached = await _cacheService.GetAsync(cacheKey);
    if (!string.IsNullOrEmpty(cached))
    {
        var cachedPost = JsonSerializer.Deserialize<PostResponse>(cached);
        if (cachedPost != null)
        {
            await OverrideRealtimeViewsAsync(cachedPost, viewsKey);
            Response.Headers["X-Cache"] = "HIT";
            return Ok(cachedPost);
        }
    }

    // 2. Cache MISS — Chiếm lock phân tán chống Cache Stampede (5 giây)
    var lockToken = Guid.NewGuid().ToString("N");
    var acquired = await _cacheService.AcquireLockAsync(lockKey, lockToken, TimeSpan.FromSeconds(5));

    if (!acquired)
    {
        // Có luồng khác đang nạp, chờ 50ms rồi thử lại
        await Task.Delay(50);
        return await GetById(id);
    }

    try
    {
        // 3. Double-check cache sau khi chiếm được lock
        cached = await _cacheService.GetAsync(cacheKey);
        if (!string.IsNullOrEmpty(cached))
        {
            var cachedPost = JsonSerializer.Deserialize<PostResponse>(cached);
            if (cachedPost != null)
            {
                await OverrideRealtimeViewsAsync(cachedPost, viewsKey);
                Response.Headers["X-Cache"] = "HIT";
                return Ok(cachedPost);
            }
        }

        // 4. Đọc dữ liệu từ MongoDB
        var filter = NotDeleted & Builders<Post>.Filter.Eq(p => p.Id, id);
        var post = await _mongo.Posts.Find(filter).FirstOrDefaultAsync();
        if (post == null)
            return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });

        var response = PostResponse.FromModel(post);
        await OverrideRealtimeViewsAsync(response, viewsKey);

        // 5. Ghi cache với TTL 10 phút
        await _cacheService.SetAsync(cacheKey, JsonSerializer.Serialize(response), CacheTtl);

        Response.Headers["X-Cache"] = "MISS";
        return Ok(response);
    }
    finally
    {
        // 6. Giải phóng lock an toàn
        await _cacheService.ReleaseLockAsync(lockKey, lockToken);
    }
}

private async Task OverrideRealtimeViewsAsync(PostResponse response, string viewsKey)
{
    var realViews = await _cacheService.GetAsync(viewsKey);
    if (!string.IsNullOrEmpty(realViews) && long.TryParse(realViews, out var v))
    {
        response.Views = v;
    }
}
```

---

## 4. Lệnh Kiểm Tra & Nghiệm Thu (Verification Commands)

```bash
dotnet test --filter "FullyQualifiedName~CacheAside"

# Kiểm tra trực tiếp trên API
curl -i http://localhost:5000/api/posts/<id> | grep "X-Cache"
```
