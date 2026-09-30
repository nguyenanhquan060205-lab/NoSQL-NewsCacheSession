namespace NewsCacheSession.Api.DTOs.Auth;

public class SessionInfoResponse
{
    public string UserId { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;

    /// <summary>"admin" hoặc "user" — frontend dùng để ẩn/hiện menu quản trị.</summary>
    public string Role { get; set; } = string.Empty;

    public string LoginAt { get; set; } = string.Empty;

    /// <summary>Giây còn lại trước khi phiên hết hạn; -1 nếu phiên không có TTL.</summary>
    public long ExpiresInSeconds { get; set; }
}
