using Microsoft.AspNetCore.Mvc;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Auth;
using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly MongoContext _mongo;
    private readonly ISessionService _sessionService;

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
        // TODO [SV1]: Implement đăng ký
        // 1. Kiểm tra username đã tồn tại chưa (MongoDB)
        // 2. Hash password (dùng BCrypt hoặc SHA256)
        // 3. Tạo User mới, lưu vào _mongo.Users
        // 4. Trả về 201 Created

        throw new NotImplementedException();
    }

    /// <summary>
    /// Đăng nhập — xác thực credentials rồi tạo Session trên Redis (Hashes + TTL).
    /// </summary>
    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        // TODO [SV1]: Implement đăng nhập
        // 1. Tìm user theo username trong MongoDB
        // 2. So sánh password hash
        // 3. Tạo sessionId = Guid.NewGuid().ToString()
        // 4. Gọi _sessionService.CreateSessionAsync(sessionId, userId, username, TTL 30 phút)
        // 5. Set Cookie "SessionId" = sessionId
        // 6. Trả về LoginResponse { SessionId, Username }

        throw new NotImplementedException();
    }

    /// <summary>
    /// Đăng xuất — xóa Session khỏi Redis.
    /// </summary>
    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        // TODO [SV1]: Implement đăng xuất
        // 1. Đọc SessionId từ Cookie hoặc Header
        // 2. Gọi _sessionService.RemoveSessionAsync(sessionId)
        // 3. Xóa Cookie "SessionId"
        // 4. Trả về 200 OK

        throw new NotImplementedException();
    }

    /// <summary>
    /// Lấy thông tin phiên đăng nhập hiện tại từ Redis Session.
    /// </summary>
    [HttpGet("me")]
    public async Task<IActionResult> Me()
    {
        // TODO [SV1]: Implement lấy thông tin session
        // 1. Đọc SessionId từ Cookie hoặc Header
        // 2. Gọi _sessionService.GetSessionAsync(sessionId)
        // 3. Nếu null → 401 Unauthorized
        // 4. Trả về SessionInfoResponse { UserId, Username, LoginAt }

        throw new NotImplementedException();
    }
}
