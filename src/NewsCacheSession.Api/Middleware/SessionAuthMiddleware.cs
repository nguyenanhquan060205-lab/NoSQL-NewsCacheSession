using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Middleware;

/// <summary>
/// Middleware xác thực phiên đăng nhập qua Redis Session (Hashes).
/// Đọc SessionId từ Cookie → kiểm tra Redis → gán user info vào HttpContext.Items.
/// </summary>
public class SessionAuthMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<SessionAuthMiddleware> _logger;

    public SessionAuthMiddleware(RequestDelegate next, ILogger<SessionAuthMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, ISessionService sessionService, IConfiguration config)
    {
        var cookieSessionId = context.Request.Cookies[CurrentUserService.SessionCookieName];
        var sessionId = cookieSessionId
                     ?? context.Request.Headers[CurrentUserService.SessionHeaderName].FirstOrDefault();

        if (!string.IsNullOrWhiteSpace(sessionId))
        {
            try
            {
                await AuthenticateAsync(context, sessionService, config, sessionId, fromCookie: cookieSessionId != null);
            }
            catch (Exception ex) when (RedisAvailability.IsOutage(ex))
            {
                // Redis sập: coi như chưa đăng nhập để trang công khai (trang chủ, chi tiết bài)
                // vẫn đọc được từ MongoDB. Endpoint cần phiên sẽ tự tra lại qua CurrentUserService,
                // gặp cùng lỗi và được RedisUnavailableMiddleware đổi thành 503.
                _logger.LogWarning("Redis không sẵn sàng, bỏ qua xác thực phiên cho {Path}: {Error}",
                    context.Request.Path, ex.Message);
            }
        }

        await _next(context);
    }

    private static async Task AuthenticateAsync(HttpContext context, ISessionService sessionService,
        IConfiguration config, string sessionId, bool fromCookie)
    {
        var session = await sessionService.GetSessionAsync(sessionId);
        if (session == null || !session.TryGetValue("userId", out var userId) || string.IsNullOrWhiteSpace(userId))
            return;

        // Hợp đồng cho CurrentUserService: gán đủ bộ UserId, Username, Role, LoginAt
        context.Items["UserId"] = userId;
        context.Items["Username"] = session.GetValueOrDefault("username", string.Empty);
        context.Items["Role"] = session.GetValueOrDefault("role", "user");
        context.Items["LoginAt"] = session.GetValueOrDefault("loginAt", string.Empty);

        // Sliding Expiration: gia hạn TTL theo cấu hình và cập nhật lastActive.
        // Phải ghi lastActive ở đây: Items đã đủ bộ nên CurrentUserService đi đường tắt,
        // không gọi TouchAsync nữa — trang quản trị phiên sẽ mãi hiện giờ đăng nhập.
        var ttl = SessionTtl.From(config);
        await sessionService.RefreshSessionAsync(sessionId, ttl);

        // Cookie cũng phải trượt theo TTL trên Redis: cookie chỉ đặt Max-Age lúc đăng nhập thì
        // trình duyệt tự xóa nó sau 30 phút, người đang dùng liên tục vẫn bị đăng xuất.
        // Phiên gửi qua header (Swagger/Postman) không có cookie để cấp lại.
        if (fromCookie)
        {
            context.Response.Cookies.Append(CurrentUserService.SessionCookieName, sessionId, new CookieOptions
            {
                HttpOnly = true,
                SameSite = SameSiteMode.Lax,
                Secure = context.Request.IsHttps,
                MaxAge = ttl
            });
        }
    }
}

/// <summary>
/// Extension method để đăng ký middleware trong Program.cs.
/// Cách dùng: app.UseSessionAuth();
/// </summary>
public static class SessionAuthMiddlewareExtensions
{
    /// <summary>
    /// Đăng ký <see cref="RedisUnavailableMiddleware"/> rồi tới <see cref="SessionAuthMiddleware"/>:
    /// middleware 503 đứng ngoài để bọc được lỗi Redis của cả middleware phiên lẫn controller.
    /// </summary>
    public static IApplicationBuilder UseSessionAuth(this IApplicationBuilder builder)
    {
        builder.UseMiddleware<RedisUnavailableMiddleware>();
        return builder.UseMiddleware<SessionAuthMiddleware>();
    }
}
