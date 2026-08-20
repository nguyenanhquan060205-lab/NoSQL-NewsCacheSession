namespace NewsCacheSession.Api.DTOs.Auth;

public class SessionInfoResponse
{
    public string UserId { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public string LoginAt { get; set; } = string.Empty;
}
