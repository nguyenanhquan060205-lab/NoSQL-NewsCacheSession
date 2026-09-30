namespace NewsCacheSession.Api.DTOs.Auth;

public class LoginResponse
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;

    /// <summary>"admin" hoặc "user" — frontend dùng để ẩn/hiện menu quản trị.</summary>
    public string Role { get; set; } = string.Empty;
}
