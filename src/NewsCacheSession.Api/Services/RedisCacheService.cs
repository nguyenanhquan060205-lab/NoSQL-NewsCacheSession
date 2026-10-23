using StackExchange.Redis;

namespace NewsCacheSession.Api.Services;

public class RedisSettings
{
    public string ConnectionString { get; set; } = string.Empty;
}

public class RedisCacheService : ICacheService
{
    private readonly IDatabase _db;
    private static long _hits;
    private static long _misses;

    public RedisCacheService(IConnectionMultiplexer redis)
    {
        _db = redis.GetDatabase();
    }

    public async Task<string?> GetAsync(string key)
    {
        var value = await _db.StringGetAsync(key);
        return value.HasValue ? value.ToString() : null;
    }

    public async Task SetAsync(string key, string value, TimeSpan ttl)
    {
        await _db.StringSetAsync(key, value, ttl);
    }

    public async Task RemoveAsync(string key)
    {
        await _db.KeyDeleteAsync(key);
    }

    public async Task<long> IncrementAsync(string key)
    {
        return await _db.StringIncrementAsync(key);
    }

    public async Task<bool> AcquireLockAsync(string key, string value, TimeSpan expiry)
    {
        return await _db.LockTakeAsync(key, value, expiry);
    }

    public async Task<bool> ReleaseLockAsync(string key, string value)
    {
        return await _db.LockReleaseAsync(key, value);
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
        await _db.SetAddAsync("posts:dirty_views", postId);
    }

    public async Task<List<string>> GetAndClearDirtyViewsAsync()
    {
        const string setKey = "posts:dirty_views";

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
