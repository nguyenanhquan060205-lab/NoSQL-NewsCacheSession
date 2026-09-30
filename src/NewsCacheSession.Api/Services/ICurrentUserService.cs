using NewsCacheSession.Api.Models;

namespace NewsCacheSession.Api.Services;

/// <summary>
/// Rút thông tin người đang đăng nhập từ Hash session trên Redis.
///
/// Gom về một chỗ vì cả AuthController, PostsController và CategoriesController đều cần
/// biết "ai đang gọi và có phải admin không". Nhận <see cref="HttpContext"/> qua tham số
/// thay vì IHttpContextAccessor để khỏi phụ thuộc trạng thái ngầm và dễ viết test.
/// </summary>
public interface ICurrentUserService
{
    /// <summary>
    /// Người đang đăng nhập, hoặc null nếu chưa đăng nhập / phiên đã hết hạn.
    /// </summary>
    Task<CurrentUser?> GetAsync(HttpContext context);

    /// <summary>Ghi role + lastActive vào Hash session mà không đụng TTL hiện có.</summary>
    Task TouchAsync(string sessionId, string role);

    /// <summary>Tra role của nhiều user bằng MỘT query — tránh N+1 khi liệt kê phiên.</summary>
    Task<Dictionary<string, string>> LookupRolesAsync(IEnumerable<string> userIds, CancellationToken ct = default);
}

/// <summary>
/// Người đang đăng nhập, đọc từ <c>session:{sessionId}</c>.
/// </summary>
public record CurrentUser(string SessionId, string UserId, string Username, string Role, string? LoginAt)
{
    public bool IsAdmin => Role == UserRoles.Admin;
}
