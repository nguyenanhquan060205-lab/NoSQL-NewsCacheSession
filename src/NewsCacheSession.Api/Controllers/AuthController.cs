using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Auth;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Api.Services;
using StackExchange.Redis;

namespace NewsCacheSession.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly MongoContext _mongo;
    private readonly ISessionService _sessionService;
    private readonly ISessionQueryService _sessionQueryService;
    private readonly ICurrentUserService _currentUser;
    private readonly IConnectionMultiplexer _redis;

    // TTL của session — xem bảng keyspace trong docs/redis-keyspace.md
    private static readonly TimeSpan SessionTtl = TimeSpan.FromMinutes(30);

    private const int MaxSessionsReturned = 200;

    public AuthController(
        MongoContext mongo,
        ISessionService sessionService,
        ISessionQueryService sessionQueryService,
        ICurrentUserService currentUser,
        IConnectionMultiplexer redis)
    {
        _mongo = mongo;
        _sessionService = sessionService;
        _sessionQueryService = sessionQueryService;
        _currentUser = currentUser;
        _redis = redis;
    }

    /// <summary>
    /// Đăng ký tài khoản mới. Lưu User vào MongoDB với password đã hash BCrypt.
    /// Tài khoản ĐẦU TIÊN của hệ thống tự động là admin (bootstrap admin).
    /// </summary>
    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        var username = request.Username.Trim();
        if (string.IsNullOrEmpty(username))
            return BadRequest(new { message = "Username không được để trống" });

        // 1. Kiểm tra username đã tồn tại chưa. Unique index users.username (MongoIndexInitializer)
        //    mới là chốt chặn thật; kiểm tra ở đây chỉ để trả lỗi 409 dễ hiểu cho người dùng.
        var exists = await _mongo.Users.Find(u => u.Username == username).AnyAsync();
        if (exists)
            return Conflict(new { message = "Username đã tồn tại" });

        // 2. Người đăng ký đầu tiên làm admin — hệ thống luôn có ít nhất một người quản trị
        //    mà không cần chèn tay vào DB hay để lộ mật khẩu admin trong file cấu hình.
        var isFirstUser = !await _mongo.Users.Find(FilterDefinition<User>.Empty).AnyAsync();

        var user = new User
        {
            Username = username,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.Password),
            Role = isFirstUser ? UserRoles.Admin : UserRoles.User,
            CreatedAt = DateTime.UtcNow
        };

        try
        {
            await _mongo.Users.InsertOneAsync(user);
        }
        catch (MongoWriteException ex) when (ex.WriteError?.Category == ServerErrorCategory.DuplicateKey)
        {
            // Hai request đăng ký cùng username chen nhau: unique index chặn ở tầng DB.
            return Conflict(new { message = "Username đã tồn tại" });
        }

        return StatusCode(StatusCodes.Status201Created, new { user.Id, user.Username, user.Role });
    }

    /// <summary>
    /// Đăng nhập — xác thực credentials rồi tạo Session trên Redis (Hashes + TTL).
    /// </summary>
    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        // 1. Tìm user theo username trong MongoDB
        var username = request.Username.Trim();
        var user = await _mongo.Users.Find(u => u.Username == username).FirstOrDefaultAsync();

        // 2. So sánh password hash. Sai username và sai password trả CÙNG một thông báo
        //    để không tiết lộ username nào có tồn tại trong hệ thống.
        if (user == null || !BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            return Unauthorized(new { message = "Sai username hoặc password" });

        // 3-4. Tạo session trên Redis: HSET session:{id} ... + EXPIRE 30 phút
        var sessionId = Guid.NewGuid().ToString();
        await _sessionService.CreateSessionAsync(sessionId, user.Id, user.Username, SessionTtl);

        // 5. Bổ sung role + lastActive vào Hash session. CreateSessionAsync (file của SV2) chưa
        //    nhận role, nên ghi thêm ở đây để middleware và trang quản trị đọc được ngay,
        //    khỏi phải query MongoDB mỗi request. HSET không làm mất TTL đã đặt ở bước trên.
        await _currentUser.TouchAsync(sessionId, user.Role);

        // 6. Set Cookie "SessionId" — HttpOnly để JavaScript không đọc được (chống XSS
        //    đánh cắp phiên); Secure bật theo scheme thật của request.
        Response.Cookies.Append(CurrentUserService.SessionCookieName, sessionId, new CookieOptions
        {
            HttpOnly = true,
            SameSite = SameSiteMode.Lax,
            Secure = Request.IsHttps,
            MaxAge = SessionTtl
        });

        return Ok(new LoginResponse
        {
            SessionId = sessionId,
            UserId = user.Id,
            Username = user.Username,
            Role = user.Role
        });
    }

    /// <summary>
    /// Đăng xuất — xóa Session khỏi Redis.
    /// </summary>
    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        var sessionId = CurrentUserService.ReadSessionId(HttpContext);
        if (!string.IsNullOrEmpty(sessionId))
            await _sessionService.RemoveSessionAsync(sessionId);

        Response.Cookies.Delete(CurrentUserService.SessionCookieName);
        return Ok(new { message = "Đăng xuất thành công" });
    }

    /// <summary>
    /// Thông tin phiên đăng nhập hiện tại, kèm số giây còn lại trước khi hết hạn.
    /// </summary>
    [HttpGet("me")]
    public async Task<IActionResult> Me()
    {
        var current = await _currentUser.GetAsync(HttpContext);
        if (current == null)
            return Unauthorized(new { message = "Chưa đăng nhập hoặc phiên đã hết hạn" });

        var ttl = await _redis.GetDatabase().KeyTimeToLiveAsync(CurrentUserService.SessionKey(current.SessionId));

        return Ok(new SessionInfoResponse
        {
            UserId = current.UserId,
            Username = current.Username,
            Role = current.Role,
            LoginAt = ToIso(current.LoginAt),
            ExpiresInSeconds = ttl.HasValue ? (long)ttl.Value.TotalSeconds : -1
        });
    }

    /// <summary>
    /// Liệt kê các phiên đang hoạt động kèm TTL còn lại — trang quản trị phiên (SCRUM-31).
    /// Chỉ admin gọi được.
    /// </summary>
    [HttpGet("sessions")]
    public async Task<IActionResult> GetActiveSessions(CancellationToken ct)
    {
        var current = await _currentUser.GetAsync(HttpContext);
        if (current == null)
            return Unauthorized(new { message = "Chưa đăng nhập hoặc phiên đã hết hạn" });

        if (!current.IsAdmin)
            return StatusCode(StatusCodes.Status403Forbidden,
                new { message = "Chỉ quản trị viên xem được danh sách phiên đăng nhập." });

        var sessions = await _sessionQueryService.ListActiveSessionsAsync(MaxSessionsReturned, ct);

        // Phiên nào chưa có field role (tạo bởi bản code cũ) thì tra bù bằng MỘT query
        // MongoDB cho tất cả, thay vì mỗi phiên một query — tránh N+1.
        var roleByUserId = await _currentUser.LookupRolesAsync(
            sessions.Where(s => string.IsNullOrEmpty(s.Role)).Select(s => s.UserId), ct);

        var items = sessions
            .Select(s => ActiveSessionResponse.FromInfo(
                s,
                string.IsNullOrEmpty(s.Role) ? roleByUserId.GetValueOrDefault(s.UserId) : s.Role,
                current.SessionId))
            .OrderByDescending(s => s.ExpiresInSeconds)
            .ToList();

        return Ok(items);
    }

    /// <summary>
    /// Buộc đăng xuất một phiên (thu hồi session). Chỉ admin gọi được.
    /// </summary>
    [HttpDelete("sessions/{sessionId}")]
    public async Task<IActionResult> RevokeSession(string sessionId)
    {
        var current = await _currentUser.GetAsync(HttpContext);
        if (current == null)
            return Unauthorized(new { message = "Chưa đăng nhập hoặc phiên đã hết hạn" });

        if (!current.IsAdmin)
            return StatusCode(StatusCodes.Status403Forbidden,
                new { message = "Chỉ quản trị viên thu hồi được phiên đăng nhập." });

        if (sessionId == current.SessionId)
            return BadRequest(new { message = "Không thể tự thu hồi phiên đang dùng — hãy dùng chức năng đăng xuất." });

        if (await _sessionService.GetSessionAsync(sessionId) == null)
            return NotFound(new { message = "Phiên không tồn tại hoặc đã hết hạn." });

        await _sessionService.RemoveSessionAsync(sessionId);
        return NoContent();
    }

    /// <summary>Redis Hash chỉ lưu string nên mốc thời gian lưu dạng Unix seconds — đổi sang ISO 8601.</summary>
    private static string ToIso(string? unixSeconds) =>
        long.TryParse(unixSeconds, out var seconds)
            ? DateTimeOffset.FromUnixTimeSeconds(seconds).ToString("o")
            : unixSeconds ?? string.Empty;
}
