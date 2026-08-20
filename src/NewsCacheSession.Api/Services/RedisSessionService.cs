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

    public async Task CreateSessionAsync(string sessionId, string userId, string username, TimeSpan ttl)
    {
        var key = Key(sessionId);
        var entries = new HashEntry[]
        {
            new("userId", userId),
            new("username", username),
            new("loginAt", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString())
        };
        await _db.HashSetAsync(key, entries);
        await _db.KeyExpireAsync(key, ttl);
    }

    public async Task<Dictionary<string, string>?> GetSessionAsync(string sessionId)
    {
        var key = Key(sessionId);
        var entries = await _db.HashGetAllAsync(key);
        if (entries.Length == 0) return null;
        return entries.ToDictionary(e => e.Name.ToString(), e => e.Value.ToString());
    }

    public async Task RefreshSessionAsync(string sessionId, TimeSpan ttl)
    {
        await _db.KeyExpireAsync(Key(sessionId), ttl);
    }

    public async Task RemoveSessionAsync(string sessionId)
    {
        await _db.KeyDeleteAsync(Key(sessionId));
    }
}
