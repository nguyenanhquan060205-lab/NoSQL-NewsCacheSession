using StackExchange.Redis;

namespace NewsCacheSession.Api.Services;

/// <summary>
/// Hiện thực <see cref="ISessionQueryService"/> bằng lệnh SCAN của Redis.
/// </summary>
public class RedisSessionQueryService : ISessionQueryService
{
    private readonly IConnectionMultiplexer _redis;
    private readonly ILogger<RedisSessionQueryService> _logger;

    // Khớp với RedisSessionService.Key() — xem bảng keyspace trong docs/redis-keyspace.md
    private const string SessionKeyPrefix = "session:";

    public RedisSessionQueryService(IConnectionMultiplexer redis, ILogger<RedisSessionQueryService> logger)
    {
        _redis = redis;
        _logger = logger;
    }

    public async Task<List<ActiveSessionInfo>> ListActiveSessionsAsync(int limit = 200, CancellationToken ct = default)
    {
        var sessions = new List<ActiveSessionInfo>();
        var db = _redis.GetDatabase();

        foreach (var endpoint in _redis.GetEndPoints())
        {
            var server = _redis.GetServer(endpoint);

            // Replica có cùng dữ liệu với primary nên quét cả hai sẽ ra phiên trùng lặp.
            if (!server.IsConnected || server.IsReplica)
                continue;

            // KeysAsync dùng SCAN (con trỏ, nhiều lượt nhỏ) chứ không phải KEYS.
            // KEYS quét toàn bộ keyspace trong một lệnh và CHẶN Redis single-thread
            // suốt thời gian đó — tuyệt đối không dùng trên server đang phục vụ.
            await foreach (var key in server.KeysAsync(db.Database, SessionKeyPrefix + "*", pageSize: 100)
                               .WithCancellation(ct))
            {
                if (sessions.Count >= limit)
                    return sessions;

                var entries = await db.HashGetAllAsync(key);

                // Phiên có thể hết hạn ngay giữa lúc quét (SCAN không phải snapshot).
                // Hash rỗng nghĩa là key đã bị Redis xóa → bỏ qua, không phải lỗi.
                if (entries.Length == 0)
                    continue;

                var fields = entries.ToDictionary(e => e.Name.ToString(), e => e.Value.ToString());
                var ttl = await db.KeyTimeToLiveAsync(key);

                sessions.Add(new ActiveSessionInfo(
                    SessionId: key.ToString()[SessionKeyPrefix.Length..],
                    UserId: fields.GetValueOrDefault("userId", string.Empty),
                    Username: fields.GetValueOrDefault("username", string.Empty),
                    Role: fields.GetValueOrDefault("role"),
                    LoginAt: fields.GetValueOrDefault("loginAt"),
                    LastActive: fields.GetValueOrDefault("lastActive"),
                    TtlSeconds: ttl.HasValue ? (long)ttl.Value.TotalSeconds : -1));
            }
        }

        _logger.LogInformation("Quét được {Count} phiên đang hoạt động.", sessions.Count);
        return sessions;
    }
}
