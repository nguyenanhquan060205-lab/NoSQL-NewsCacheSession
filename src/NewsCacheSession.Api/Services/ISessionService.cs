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
