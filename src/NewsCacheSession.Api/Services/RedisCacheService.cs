using StackExchange.Redis;

namespace NewsCacheSession.Api.Services;

public class RedisSettings
{
    public string ConnectionString { get; set; } = string.Empty;
}

public class RedisCacheService : ICacheService
{
    private readonly IConnectionMultiplexer _redis;
    private readonly IDatabase _db;
    private readonly ILogger<RedisCacheService> _logger;
    private static long _hits;
    private static long _misses;

    public RedisCacheService(IConnectionMultiplexer redis, ILogger<RedisCacheService> logger)
    {
        _redis = redis;
        _db = redis.GetDatabase();
        _logger = logger;
    }

    // Cache chỉ là bản sao của MongoDB: Redis sập thì coi như MISS để request đọc thẳng DB gốc,
    // thay vì kéo cả trang chủ/trang chi tiết sập theo.
    public async Task<string?> GetAsync(string key)
    {
        try
        {
            RedisAvailability.EnsureConnected(_redis);
            var value = await _db.StringGetAsync(key);
            return value.HasValue ? value.ToString() : null;
        }
        catch (Exception ex) when (RedisAvailability.IsOutage(ex))
        {
            _logger.LogWarning("Redis không sẵn sàng, đọc {Key} coi như MISS: {Error}", key, ex.Message);
            return null;
        }
    }

    // Ghi/xóa cache lỗi thì bỏ qua: bản cache (nếu còn) tự hết hạn theo TTL.
    public async Task SetAsync(string key, string value, TimeSpan ttl)
    {
        try
        {
            RedisAvailability.EnsureConnected(_redis);
            await _db.StringSetAsync(key, value, ttl);
        }
        catch (Exception ex) when (RedisAvailability.IsOutage(ex))
        {
            _logger.LogError("Redis không sẵn sàng, bỏ qua ghi cache {Key}: {Error}", key, ex.Message);
        }
    }

    public async Task RemoveAsync(string key)
    {
        try
        {
            RedisAvailability.EnsureConnected(_redis);
            await _db.KeyDeleteAsync(key);
        }
        catch (Exception ex) when (RedisAvailability.IsOutage(ex))
        {
            _logger.LogError("Redis không sẵn sàng, không xóa được cache {Key} — bản cũ sống tối đa hết TTL: {Error}",
                key, ex.Message);
        }
    }

    // Các thao tác dưới đây cần giá trị thật từ Redis (bộ đếm, lock) nên vẫn ném lỗi —
    // RedisUnavailableMiddleware đổi lỗi này thành 503.
    public async Task<long> IncrementAsync(string key)
    {
        RedisAvailability.EnsureConnected(_redis);
        return await _db.StringIncrementAsync(key);
    }

    public async Task<bool> SetIfNotExistsAsync(string key, string value)
    {
        RedisAvailability.EnsureConnected(_redis);
        return await _db.StringSetAsync(key, value, when: When.NotExists);
    }

    public async Task<bool> AcquireLockAsync(string key, string value, TimeSpan expiry)
    {
        RedisAvailability.EnsureConnected(_redis);
        return await _db.LockTakeAsync(key, value, expiry);
    }

    public async Task<bool> ReleaseLockAsync(string key, string value)
    {
        try
        {
            RedisAvailability.EnsureConnected(_redis);
            return await _db.LockReleaseAsync(key, value);
        }
        catch (Exception ex) when (RedisAvailability.IsOutage(ex))
        {
            // Lock có TTL nên tự hết hạn; không được làm hỏng response đã đọc xong từ MongoDB.
            _logger.LogWarning("Redis không sẵn sàng, để lock {Key} tự hết hạn: {Error}", key, ex.Message);
            return false;
        }
    }

    public void RecordLookup(bool hit)
    {
        if (hit)
            Interlocked.Increment(ref _hits);
        else
            Interlocked.Increment(ref _misses);
    }

    public CacheStats GetStats()
    {
        return new CacheStats
        {
            Hits = Interlocked.Read(ref _hits),
            Misses = Interlocked.Read(ref _misses)
        };
    }

    public async Task MarkDirtyViewAsync(string postId)
    {
        RedisAvailability.EnsureConnected(_redis);
        await _db.SetAddAsync("posts:dirty_views", postId);
    }

    public async Task<List<string>> GetAndClearDirtyViewsAsync()
    {
        const string setKey = "posts:dirty_views";
        RedisAvailability.EnsureConnected(_redis);

        // SPOP lấy và xóa trong cùng một lệnh nguyên tử. SMEMBERS rồi DEL thì ID nào được SADD
        // chen vào giữa hai lệnh sẽ bị xóa mất dấu mà chưa kịp đồng bộ về MongoDB.
        // ID thêm vào sau SCARD vẫn nằm lại trong Set, lượt flush sau sẽ lấy.
        var count = await _db.SetLengthAsync(setKey);
        if (count == 0) return new List<string>();

        var members = await _db.SetPopAsync(setKey, count);
        return members.Select(m => m.ToString()).Where(s => !string.IsNullOrEmpty(s)).ToList();
    }

    public static void ResetStats()
    {
        Interlocked.Exchange(ref _hits, 0);
        Interlocked.Exchange(ref _misses, 0);
    }
}
