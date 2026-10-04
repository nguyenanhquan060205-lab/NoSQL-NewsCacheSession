# Redis Caching & Patterns Guide (StackExchange.Redis)

Hướng dẫn chi tiết triển khai các pattern Redis trong ASP.NET Core cho đề tài NoSQL-NewsCacheSession.

---

## 1. Cache-Aside với Chống Cache Stampede

### 1.1. Luồng hoạt động chuẩn
```text
Client -> GET /api/posts/{id}
             |
      [Redis: GET post:{id}]
       /                  \
   (HIT)                  (MISS)
    /                        \
[Đọc post:{id}:views]    [Lấy lock:post:{id} (SET NX PX 5000)]
   |                              |
[Trả về X-Cache: HIT]    [Đọc từ MongoDB] -> [Ghi post:{id} EX 600]
                                  |
                           [Giải phóng lock]
                                  |
                         [Trả về X-Cache: MISS]
```

### 1.2. Mẫu triển khai trong C# (C# Implementation Pattern)
```csharp
public async Task<PostResponse?> GetPostByIdWithCacheAsync(string id)
{
    var cacheKey = $"post:{id}";
    var viewsKey = $"post:{id}:views";
    var lockKey = $"lock:post:{id}";

    // 1. Thử đọc từ Cache
    var cached = await _redisDb.StringGetAsync(cacheKey);
    if (cached.HasValue)
    {
        var response = JsonSerializer.Deserialize<PostResponse>(cached!);
        // Đồng bộ số view mới nhất từ counter
        var views = await _redisDb.StringGetAsync(viewsKey);
        if (views.HasValue && long.TryParse(views, out var currentViews))
        {
            response.Views = currentViews;
        }

        HttpContext.Response.Headers["X-Cache"] = "HIT";
        return response;
    }

    // 2. Cache MISS - Chiếm khóa phân tán chống Stampede
    var lockValue = Guid.NewGuid().ToString("N");
    var lockAcquired = await _redisDb.StringSetAsync(
        lockKey,
        lockValue,
        TimeSpan.FromSeconds(5),
        When.NotExists
    );

    if (!lockAcquired)
    {
        // Đang có luồng khác nạp dữ liệu, chờ ngắn rồi đọc lại cache
        await Task.Delay(50);
        return await GetPostByIdWithCacheAsync(id);
    }

    try
    {
        // 3. Double-check cache sau khi chiếm được lock
        cached = await _redisDb.StringGetAsync(cacheKey);
        if (cached.HasValue)
        {
            HttpContext.Response.Headers["X-Cache"] = "HIT";
            return JsonSerializer.Deserialize<PostResponse>(cached!);
        }

        // 4. Đọc dữ liệu gốc từ MongoDB
        var post = await _mongoContext.Posts
            .Find(p => p.Id == id && !p.IsDeleted)
            .FirstOrDefaultAsync();

        if (post == null) return null;

        var result = MapToResponse(post);

        // 5. Ghi cache với TTL 10 phút
        var json = JsonSerializer.Serialize(result);
        await _redisDb.StringSetAsync(cacheKey, json, TimeSpan.FromMinutes(10));

        HttpContext.Response.Headers["X-Cache"] = "MISS";
        return result;
    }
    finally
    {
        // 6. Giải phóng lock (an toàn qua Lua Script kiểm tra token)
        const string releaseScript = @"
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end";
        await _redisDb.ScriptEvaluateAsync(releaseScript, new RedisKey[] { lockKey }, new RedisValue[] { lockValue });
    }
}
```

---

## 2. Invalidation Cache Danh Sách Bằng Số Phiên Bản (Versioned Keys)

Thay vì dùng `SCAN` + `DEL` (chậm và block event loop Redis khi có nhiều key), áp dụng kỹ thuật số phiên bản:

### Cơ chế:
- Key danh sách: `posts:cat:{categoryId}:p{page}:v{ver}`
- Key lưu phiên bản: `posts:ver` (không TTL)
- Khi thêm, sửa hoặc xóa bài viết:
  1. Ghi dữ liệu vào MongoDB trước.
  2. Xóa cache chi tiết: `DEL post:{id}`.
  3. Tăng số phiên bản: `INCR posts:ver`.
  4. Lập tức mọi key danh sách phiên bản cũ (`v1`, `v2`...) trở thành rác và tự hết hạn theo TTL 3 phút mà không cần xóa chủ động.

```csharp
public async Task BumpListVersionAsync()
{
    await _redisDb.StringIncrementAsync("posts:ver");
}
```

---

## 3. Atomic Counter Lượt Xem (`post:{id}:views`)

- **Tăng view**:
  ```csharp
  var currentViews = await _redisDb.StringIncrementAsync($"post:{id}:views");
  ```
- **Sync về MongoDB**:
  Để đảm bảo tính nhất quán cuối cùng (eventual consistency), tạo background job chạy mỗi 1-5 phút quét các key views hoặc cập nhật lô về MongoDB.
