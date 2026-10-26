namespace NewsCacheSession.Api.Services;

public class CacheStats
{
    public long Hits { get; set; }
    public long Misses { get; set; }
    public long TotalRequests => Hits + Misses;
    public double HitRate => TotalRequests == 0 ? 0 : Math.Round((double)Hits / TotalRequests * 100, 2);
}

/// <summary>
/// Truy cập cache Redis. Khi Redis sập: <see cref="GetAsync"/> trả null (coi như MISS),
/// <see cref="SetAsync"/>/<see cref="RemoveAsync"/>/<see cref="ReleaseLockAsync"/> bỏ qua và ghi log;
/// các thao tác cần giá trị thật (bộ đếm, lock, Set dirty) ném lỗi để
/// <see cref="RedisAvailability.IsOutage"/> nhận ra.
/// </summary>
public interface ICacheService
{
    Task<string?> GetAsync(string key);
    Task SetAsync(string key, string value, TimeSpan ttl);
    Task RemoveAsync(string key);
    Task<long> IncrementAsync(string key);

    /// <summary>
    /// Ghi key KHÔNG TTL chỉ khi key chưa tồn tại (SET NX). Trả về false nếu key đã có giá trị.
    /// </summary>
    Task<bool> SetIfNotExistsAsync(string key, string value);
    Task<bool> AcquireLockAsync(string key, string value, TimeSpan expiry);
    Task<bool> ReleaseLockAsync(string key, string value);

    /// <summary>
    /// Ghi nhận kết quả tra cache của MỘT request (khớp header X-Cache). GetAsync không tự đếm,
    /// vì nó còn dùng để đọc bộ đếm views và posts:ver — không phải lượt tra cache.
    /// </summary>
    void RecordLookup(bool hit);
    CacheStats GetStats();
    Task MarkDirtyViewAsync(string postId);
    Task<List<string>> GetAndClearDirtyViewsAsync();
}
