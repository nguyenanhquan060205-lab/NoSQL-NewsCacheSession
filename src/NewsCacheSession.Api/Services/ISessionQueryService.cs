namespace NewsCacheSession.Api.Services;

/// <summary>
/// Đọc/liệt kê các phiên đang hoạt động trên Redis — phục vụ trang quản trị phiên (SCRUM-31).
///
/// Tách riêng khỏi <see cref="ISessionService"/> theo hướng CQRS: ISessionService lo
/// vòng đời một phiên (tạo / đọc / gia hạn / xóa), còn interface này chỉ đọc để quản trị.
/// Nhờ vậy hai phần việc không đụng cùng file, và phần quản trị có thể thêm bộ lọc,
/// phân trang, thống kê về sau mà không làm phình interface dùng ở hot path.
/// </summary>
public interface ISessionQueryService
{
    /// <summary>
    /// Liệt kê các phiên đang còn sống, kèm TTL còn lại (giây).
    /// </summary>
    /// <param name="limit">Chặn trên số phiên trả về, tránh quét vô hạn khi keyspace lớn.</param>
    Task<List<ActiveSessionInfo>> ListActiveSessionsAsync(int limit = 200, CancellationToken ct = default);
}

/// <summary>
/// Một phiên đang hoạt động đọc từ Hash <c>session:{sessionId}</c>.
/// </summary>
/// <param name="TtlSeconds">Giây còn lại trước khi phiên tự hết hạn; -1 nghĩa là key không có TTL.</param>
public record ActiveSessionInfo(
    string SessionId,
    string UserId,
    string Username,
    string? Role,
    string? LoginAt,
    string? LastActive,
    long TtlSeconds);
