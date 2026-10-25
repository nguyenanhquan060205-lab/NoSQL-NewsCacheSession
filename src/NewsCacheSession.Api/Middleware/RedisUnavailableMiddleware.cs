using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Middleware;

/// <summary>
/// Đổi lỗi "Redis không sẵn sàng" thành 503 JSON tiếng Việt thay vì 500.
///
/// Đọc bài viết vẫn chạy khi Redis sập (cache coi như MISS, đọc thẳng MongoDB), nhưng đăng nhập,
/// kiểm tra phiên, đếm lượt xem thì bắt buộc cần Redis — các thao tác đó trả 503 để frontend
/// và người dùng biết lỗi tạm thời, không phải lỗi dữ liệu.
///
/// Phải đứng TRƯỚC <see cref="SessionAuthMiddleware"/> để bọc được cả middleware phiên lẫn
/// controller — <see cref="SessionAuthMiddlewareExtensions.UseSessionAuth"/> đăng ký đúng thứ tự này.
/// </summary>
public class RedisUnavailableMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RedisUnavailableMiddleware> _logger;

    public RedisUnavailableMiddleware(RequestDelegate next, ILogger<RedisUnavailableMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex) when (RedisAvailability.IsOutage(ex) && !context.Response.HasStarted)
        {
            _logger.LogError("Redis không sẵn sàng khi xử lý {Method} {Path}: {Error}",
                context.Request.Method, context.Request.Path, ex.Message);

            context.Response.Clear();
            context.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
            await context.Response.WriteAsJsonAsync(new
            {
                message = "Redis tạm thời không sẵn sàng nên chưa đăng nhập, kiểm tra phiên hay đếm lượt xem được. Vui lòng thử lại sau."
            });
        }
    }
}
