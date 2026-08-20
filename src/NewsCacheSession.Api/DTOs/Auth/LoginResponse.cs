namespace NewsCacheSession.Api.DTOs.Auth;

public class LoginResponse
{
    public string SessionId { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
}
