using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.DTOs.Auth;

/// <summary>
/// Một phiên đang hoạt động, trả về cho trang quản trị phiên (SCRUM-31).
/// </summary>
public class ActiveSessionResponse
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public string LoginAt { get; set; } = string.Empty;
    public string LastActive { get; set; } = string.Empty;

    /// <summary>Giây còn lại trước khi phiên tự hết hạn; -1 nếu key không có TTL.</summary>
    public long ExpiresInSeconds { get; set; }

    /// <summary>true nếu đây chính là phiên đang gửi request (frontend không nên cho tự đăng xuất mình).</summary>
    public bool IsCurrent { get; set; }

    public static ActiveSessionResponse FromInfo(ActiveSessionInfo info, string? role, string? currentSessionId) => new()
    {
        SessionId = info.SessionId,
        UserId = info.UserId,
        Username = info.Username,
        Role = role ?? string.Empty,
        LoginAt = ToIso(info.LoginAt),
        LastActive = ToIso(info.LastActive),
        ExpiresInSeconds = info.TtlSeconds,
        IsCurrent = info.SessionId == currentSessionId
    };

    /// <summary>Redis Hash chỉ lưu được string nên thời điểm lưu dạng Unix seconds — đổi sang ISO 8601.</summary>
    private static string ToIso(string? unixSeconds) =>
        long.TryParse(unixSeconds, out var seconds)
            ? DateTimeOffset.FromUnixTimeSeconds(seconds).ToString("o")
            : unixSeconds ?? string.Empty;
}
