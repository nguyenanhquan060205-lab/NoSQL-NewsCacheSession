namespace NewsCacheSession.Api.Services;

public class CacheStats
{
    public long Hits { get; set; }
    public long Misses { get; set; }
    public long TotalRequests => Hits + Misses;
    public double HitRate => TotalRequests == 0 ? 0 : Math.Round((double)Hits / TotalRequests * 100, 2);
}

public interface ICacheService
{
    Task<string?> GetAsync(string key);
    Task SetAsync(string key, string value, TimeSpan ttl);
    Task RemoveAsync(string key);
    Task<long> IncrementAsync(string key);
    Task<bool> AcquireLockAsync(string key, string value, TimeSpan expiry);
    Task<bool> ReleaseLockAsync(string key, string value);
    CacheStats GetStats();
    Task MarkDirtyViewAsync(string postId);
    Task<List<string>> GetAndClearDirtyViewsAsync();
}
