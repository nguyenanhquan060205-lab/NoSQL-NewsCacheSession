using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Middleware;

/// <summary>
/// Middleware xác thực phiên đăng nhập qua Redis Session (Hashes).
/// Đọc SessionId từ Cookie → kiểm tra Redis → gán user info vào HttpContext.Items.
/// </summary>
public class SessionAuthMiddleware
{
    private readonly RequestDelegate _next;

    public SessionAuthMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context, ISessionService sessionService, IConfiguration config)
    {
        var sessionId = context.Request.Cookies[CurrentUserService.SessionCookieName]
                     ?? context.Request.Headers[CurrentUserService.SessionHeaderName].FirstOrDefault();

        if (!string.IsNullOrWhiteSpace(sessionId))
        {
            var session = await sessionService.GetSessionAsync(sessionId);
            if (session != null && session.TryGetValue("userId", out var userId) && !string.IsNullOrWhiteSpace(userId))
            {
                // Hợp đồng cho CurrentUserService: gán đủ bộ UserId, Username, Role, LoginAt
                context.Items["UserId"] = userId;
                context.Items["Username"] = session.GetValueOrDefault("username", string.Empty);
                context.Items["Role"] = session.GetValueOrDefault("role", "user");
                context.Items["LoginAt"] = session.GetValueOrDefault("loginAt", string.Empty);

                // Sliding Expiration: đọc cấu hình TTL và gia hạn thêm
                var ttlMinutes = config.GetValue<int>("SessionSettings:TtlMinutes", 30);
                var ttl = TimeSpan.FromMinutes(ttlMinutes > 0 ? ttlMinutes : 30);
                await sessionService.RefreshSessionAsync(sessionId, ttl);
            }
        }

        await _next(context);
    }
}

/// <summary>
/// Extension method để đăng ký middleware trong Program.cs.
/// Cách dùng: app.UseSessionAuth();
/// </summary>
public static class SessionAuthMiddlewareExtensions
{
    public static IApplicationBuilder UseSessionAuth(this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<SessionAuthMiddleware>();
    }
}
