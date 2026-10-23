using StackExchange.Redis;

namespace NewsCacheSession.Api.Services;

public class RedisSessionService : ISessionService
{
    private readonly IDatabase _db;

    public RedisSessionService(IConnectionMultiplexer redis)
    {
        _db = redis.GetDatabase();
    }

    private static string Key(string sessionId) => $"session:{sessionId}";

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

    public Task CreateSessionAsync(string sessionId, string userId, string username, TimeSpan ttl) =>
        CreateSessionAsync(sessionId, userId, username, "user", ttl);

    public async Task<Dictionary<string, string>?> GetSessionAsync(string sessionId)
    {
        var key = Key(sessionId);
        var entries = await _db.HashGetAllAsync(key);
        if (entries.Length == 0) return null;
        return entries.ToDictionary(e => e.Name.ToString(), e => e.Value.ToString());
    }

    public async Task RefreshSessionAsync(string sessionId, TimeSpan ttl)
    {
        var key = Key(sessionId);

        // Gia hạn TTL + ghi lastActive trong một transaction, chỉ chạy khi key còn tồn tại:
        // phiên vừa hết hạn hoặc bị admin thu hồi mà HSET vẫn chạy thì sẽ tạo lại một Hash
        // không TTL, nằm vĩnh viễn trong Redis.
        var tran = _db.CreateTransaction();
        tran.AddCondition(Condition.KeyExists(key));
        _ = tran.HashSetAsync(key, "lastActive", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString());
        _ = tran.KeyExpireAsync(key, ttl);
        await tran.ExecuteAsync();
    }

    public async Task RemoveSessionAsync(string sessionId)
    {
        await _db.KeyDeleteAsync(Key(sessionId));
    }
}
