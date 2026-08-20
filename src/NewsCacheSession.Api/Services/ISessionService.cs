namespace NewsCacheSession.Api.Services;

public interface ISessionService
{
    Task CreateSessionAsync(string sessionId, string userId, string username, TimeSpan ttl);
    Task<Dictionary<string, string>?> GetSessionAsync(string sessionId);
    Task RefreshSessionAsync(string sessionId, TimeSpan ttl);
    Task RemoveSessionAsync(string sessionId);
}
