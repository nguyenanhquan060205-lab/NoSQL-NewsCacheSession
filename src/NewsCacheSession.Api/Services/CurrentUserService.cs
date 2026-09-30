using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.Models;
using StackExchange.Redis;

namespace NewsCacheSession.Api.Services;

/// <summary>
/// Hiện thực <see cref="ICurrentUserService"/> dựa trên Hash session của Redis.
/// </summary>
public class CurrentUserService : ICurrentUserService
{
    private readonly ISessionService _sessionService;
    private readonly MongoContext _mongo;
    private readonly IConnectionMultiplexer _redis;

    public const string SessionCookieName = "SessionId";
    public const string SessionHeaderName = "X-Session-Id";

    public CurrentUserService(ISessionService sessionService, MongoContext mongo, IConnectionMultiplexer redis)
    {
        _sessionService = sessionService;
        _mongo = mongo;
        _redis = redis;
    }

    public static string SessionKey(string sessionId) => $"session:{sessionId}";

    /// <summary>
    /// Đọc SessionId từ Cookie, fallback sang header <c>X-Session-Id</c> để frontend khác
    /// origin hoặc Swagger/Postman (nơi cookie bị chặn) vẫn xác thực được.
    /// </summary>
    public static string? ReadSessionId(HttpContext context) =>
        context.Request.Cookies[SessionCookieName]
        ?? context.Request.Headers[SessionHeaderName].FirstOrDefault();

    public async Task<CurrentUser?> GetAsync(HttpContext context)
    {
        var sessionId = ReadSessionId(context);
        if (string.IsNullOrEmpty(sessionId))
            return null;

        // Đường tắt: nếu SessionAuthMiddleware (SV2) đã đọc session và gán vào HttpContext.Items
        // thì dùng luôn, khỏi HGETALL lần hai trong cùng một request.
        // HỢP ĐỒNG cho SV2 — middleware cần gán ĐỦ BỘ, thiếu Role thì đường tắt bị bỏ qua:
        //     context.Items["UserId"], ["Username"], ["Role"]
        if (context.Items["UserId"] is string ctxUserId && !string.IsNullOrEmpty(ctxUserId) &&
            context.Items["Role"] is string ctxRole && !string.IsNullOrEmpty(ctxRole))
        {
            return new CurrentUser(
                sessionId,
                ctxUserId,
                context.Items["Username"] as string ?? string.Empty,
                ctxRole,
                context.Items["LoginAt"] as string);
        }

        // HGETALL session:{id} — null nghĩa là phiên không tồn tại hoặc đã hết hạn (TTL)
        var session = await _sessionService.GetSessionAsync(sessionId);
        if (session == null)
            return null;

        var userId = session.GetValueOrDefault("userId", string.Empty);
        if (string.IsNullOrEmpty(userId))
            return null;

        // role được ghi vào Hash session lúc đăng nhập nên đường đọc/ghi thường KHÔNG tốn
        // query MongoDB. Phiên tạo bởi bản code cũ chưa có field role thì tra bù một lần
        // rồi ghi lại vào Hash để các request sau khỏi tra nữa.
        var role = session.GetValueOrDefault("role");
        if (string.IsNullOrEmpty(role))
        {
            role = await LookupRoleAsync(userId);
            await TouchAsync(sessionId, role);
        }

        return new CurrentUser(
            sessionId,
            userId,
            session.GetValueOrDefault("username", string.Empty),
            role,
            session.GetValueOrDefault("loginAt"));
    }

    /// <summary>
    /// Ghi role + lastActive vào Hash session. HSET trên key đã tồn tại KHÔNG xóa TTL,
    /// nên phiên không bị gia hạn hay mất hạn ngoài ý muốn.
    /// </summary>
    public async Task TouchAsync(string sessionId, string role)
    {
        await _redis.GetDatabase().HashSetAsync(SessionKey(sessionId), new[]
        {
            new HashEntry("role", role),
            new HashEntry("lastActive", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString())
        });
    }

    /// <summary>
    /// Tra role của một user. Thiếu thông tin thì trả về quyền thấp nhất ("user") —
    /// mặc định an toàn: không rõ thì từ chối, chứ không cho qua.
    /// </summary>
    public async Task<string> LookupRoleAsync(string userId)
    {
        if (string.IsNullOrEmpty(userId))
            return UserRoles.User;

        var role = await _mongo.Users.Find(u => u.Id == userId)
            .Project(u => u.Role)
            .FirstOrDefaultAsync();

        return string.IsNullOrEmpty(role) ? UserRoles.User : role;
    }

    /// <summary>
    /// Tra role của nhiều user bằng MỘT query (tránh N+1 khi liệt kê phiên đăng nhập).
    /// </summary>
    public async Task<Dictionary<string, string>> LookupRolesAsync(IEnumerable<string> userIds, CancellationToken ct = default)
    {
        var ids = userIds.Where(id => !string.IsNullOrEmpty(id)).Distinct().ToList();
        if (ids.Count == 0)
            return new Dictionary<string, string>();

        var users = await _mongo.Users
            .Find(Builders<User>.Filter.In(u => u.Id, ids))
            .Project(u => new UserRoleProjection { Id = u.Id, Role = u.Role })
            .ToListAsync(ct);

        return users.ToDictionary(u => u.Id, u => u.Role);
    }

    private class UserRoleProjection
    {
        public string Id { get; set; } = string.Empty;
        public string Role { get; set; } = string.Empty;
    }
}
