using Microsoft.AspNetCore.Mvc;
using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Auth;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly MongoContext _mongo;
    private readonly ISessionService _sessionService;

    // Tên cookie/header chứa SessionId & TTL của session (xem docs/redis-keyspace.md)
    private const string SessionCookieName = "SessionId";
    private const string SessionHeaderName = "X-Session-Id";
    private static readonly TimeSpan SessionTtl = TimeSpan.FromMinutes(30);

    public AuthController(MongoContext mongo, ISessionService sessionService)
    {
        _mongo = mongo;
        _sessionService = sessionService;
    }

    /// <summary>
    /// Đăng ký tài khoản mới.
    /// Lưu User vào MongoDB với password đã hash.
    /// </summary>
    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        var username = request.Username.Trim();
        if (string.IsNullOrEmpty(username))
            return BadRequest(new { message = "Username không được để trống" });

        // 1. Kiểm tra username đã tồn tại chưa
        var exists = await _mongo.Users.Find(u => u.Username == username).AnyAsync();
        if (exists)
            return Conflict(new { message = "Username đã tồn tại" });

        // 2. Hash password bằng BCrypt
        // 3. Tạo User mới, lưu vào MongoDB
        var user = new User
        {
            Username = username,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.Password),
            CreatedAt = DateTime.UtcNow
        };
        await _mongo.Users.InsertOneAsync(user);

        // 4. Trả về 201 Created
        return StatusCode(StatusCodes.Status201Created, new { user.Id, user.Username });
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

        // 2. So sánh password hash (trả cùng 1 thông báo để không lộ username có tồn tại hay không)
        if (user == null || !BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            return Unauthorized(new { message = "Sai username hoặc password" });

        // 3-4. Tạo session trên Redis: HSET session:{id} ... + EXPIRE 30 phút
        var sessionId = Guid.NewGuid().ToString();
        await _sessionService.CreateSessionAsync(sessionId, user.Id, user.Username, SessionTtl);

        // 5. Set Cookie "SessionId"
        Response.Cookies.Append(SessionCookieName, sessionId, new CookieOptions
        {
            HttpOnly = true,
            SameSite = SameSiteMode.Lax,
            Secure = Request.IsHttps,
            MaxAge = SessionTtl
        });

        // 6. Trả về LoginResponse
        return Ok(new LoginResponse { SessionId = sessionId, Username = user.Username });
    }

    /// <summary>
    /// Đăng xuất — xóa Session khỏi Redis.
    /// </summary>
    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        // 1. Đọc SessionId từ Cookie hoặc Header
        var sessionId = GetSessionId();

        // 2. Xóa session trên Redis (DEL session:{id})
        if (!string.IsNullOrEmpty(sessionId))
            await _sessionService.RemoveSessionAsync(sessionId);

        // 3. Xóa Cookie "SessionId"
        Response.Cookies.Delete(SessionCookieName);

        // 4. Trả về 200 OK
        return Ok(new { message = "Đăng xuất thành công" });
    }

    /// <summary>
    /// Lấy thông tin phiên đăng nhập hiện tại từ Redis Session.
    /// </summary>
    [HttpGet("me")]
    public async Task<IActionResult> Me()
    {
        // 1. Đọc SessionId từ Cookie hoặc Header
        var sessionId = GetSessionId();
        if (string.IsNullOrEmpty(sessionId))
            return Unauthorized(new { message = "Chưa đăng nhập" });

        // 2-3. HGETALL session:{id} — null nghĩa là session không tồn tại/đã hết hạn
        var session = await _sessionService.GetSessionAsync(sessionId);
        if (session == null)
            return Unauthorized(new { message = "Phiên đăng nhập không hợp lệ hoặc đã hết hạn" });

        // 4. Trả về SessionInfoResponse (loginAt lưu dạng Unix seconds → đổi sang ISO 8601)
        var loginAt = session.GetValueOrDefault("loginAt", string.Empty);
        if (long.TryParse(loginAt, out var unixSeconds))
            loginAt = DateTimeOffset.FromUnixTimeSeconds(unixSeconds).ToString("o");

        return Ok(new SessionInfoResponse
        {
            UserId = session.GetValueOrDefault("userId", string.Empty),
            Username = session.GetValueOrDefault("username", string.Empty),
            LoginAt = loginAt
        });
    }

    private string? GetSessionId() =>
        Request.Cookies[SessionCookieName] ?? Request.Headers[SessionHeaderName].FirstOrDefault();
}
