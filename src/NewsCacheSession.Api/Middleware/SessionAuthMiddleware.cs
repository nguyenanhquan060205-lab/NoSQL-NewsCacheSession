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

    public async Task InvokeAsync(HttpContext context, ISessionService sessionService)
    {
        // TODO [SV2]: Implement Session Authentication Middleware
        // 1. Đọc SessionId từ Cookie "SessionId" hoặc Header "X-Session-Id"
        //    var sessionId = context.Request.Cookies["SessionId"]
        //                 ?? context.Request.Headers["X-Session-Id"].FirstOrDefault();
        //
        // 2. Nếu có sessionId → gọi sessionService.GetSessionAsync(sessionId)
        //
        // 3. Nếu session hợp lệ (không null):
        //    - context.Items["UserId"] = session["userId"];
        //    - context.Items["Username"] = session["username"];
        //    - (Tuỳ chọn) Refresh TTL: await sessionService.RefreshSessionAsync(sessionId, TTL)
        //
        // 4. Nếu không có session → không làm gì, để Controller tự quyết 401
        //
        // 5. Gọi tiếp pipeline:
        //    await _next(context);

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
