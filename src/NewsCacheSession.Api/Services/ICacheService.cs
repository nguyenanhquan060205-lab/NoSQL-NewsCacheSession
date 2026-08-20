namespace NewsCacheSession.Api.Services;

public interface ICacheService
{
    Task<string?> GetAsync(string key);
    Task SetAsync(string key, string value, TimeSpan ttl);
    Task RemoveAsync(string key);
    Task<long> IncrementAsync(string key);
}
