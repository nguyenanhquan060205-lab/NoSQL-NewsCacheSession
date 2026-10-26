namespace NewsCacheSession.Api.Services;

public interface ISessionService
{
    Task CreateSessionAsync(string sessionId, string userId, string username, string role, TimeSpan ttl);
    Task CreateSessionAsync(string sessionId, string userId, string username, TimeSpan ttl);
    Task<Dictionary<string, string>?> GetSessionAsync(string sessionId);
    /// <summary>Gia hạn TTL (sliding) và cập nhật <c>lastActive</c>; bỏ qua nếu phiên không còn.</summary>
    Task RefreshSessionAsync(string sessionId, TimeSpan ttl);
    Task RemoveSessionAsync(string sessionId);
}

/// <summary>
/// TTL phiên đọc từ <c>SessionSettings:TtlMinutes</c> — một nguồn duy nhất cho Hash session,
/// cookie lúc đăng nhập và sliding expiration ở middleware.
/// </summary>
public static class SessionTtl
{
    private const int DefaultMinutes = 30;

    public static TimeSpan From(IConfiguration config)
    {
        var minutes = config.GetValue("SessionSettings:TtlMinutes", DefaultMinutes);
        return TimeSpan.FromMinutes(minutes > 0 ? minutes : DefaultMinutes);
    }
}
