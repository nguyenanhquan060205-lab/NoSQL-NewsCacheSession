# Session Management & Authentication Guide

Hướng dẫn kiến trúc quản lý phiên bằng Redis Hashes và cơ chế xác thực trong ASP.NET Core.

---

## 1. Lưu Trữ Session Bằng Redis Hash

Theo đề tài, cấu trúc **Redis Hash** được sử dụng để lưu Session người dùng thay vì String JSON thông thường.

### Cấu trúc Key & Fields:
- Key: `session:{sessionId}`
- Kiểu dữ liệu: `Hash`
- TTL: 30 phút (Gia hạn sliding theo từng request)
- Fields:
  - `userId`: ID của người dùng trong MongoDB.
  - `username`: Tên tài khoản.
  - `role`: Vai trò (`admin` hoặc `user`). Lưu trực tiếp vào Hash để phân quyền mà không cần query lại MongoDB.
  - `loginAt`: Thời điểm đăng nhập (ISO 8601 string).
  - `lastActive`: Thời điểm request gần nhất (cập nhật qua `HSET`).

---

## 2. SessionAuthMiddleware Pipeline

Middleware chặn các request, kiểm tra cookie/header chứa `sessionId`:

```csharp
public class SessionAuthMiddleware
{
    private readonly RequestDelegate _next;

    public SessionAuthMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context, IConnectionMultiplexer redis)
    {
        // 1. Trích xuất sessionId từ Cookie hoặc Authorization header
        if (!context.Request.Cookies.TryGetValue("SessionId", out var sessionId) || string.IsNullOrEmpty(sessionId))
        {
            if (context.Request.Headers.TryGetValue("X-Session-Id", out var headerVal))
            {
                sessionId = headerVal.ToString();
            }
        }

        if (!string.IsNullOrEmpty(sessionId))
        {
            var db = redis.GetDatabase();
            var sessionKey = $"session:{sessionId}";

            var entries = await db.HashGetAllAsync(sessionKey);
            if (entries.Length > 0)
            {
                var dict = entries.ToDictionary(
                    x => x.Name.ToString(),
                    x => x.Value.ToString()
                );

                // 2. Gán đủ bộ hợp đồng vào HttpContext.Items (cho CurrentUserService)
                if (dict.TryGetValue("userId", out var userId)) context.Items["UserId"] = userId;
                if (dict.TryGetValue("username", out var username)) context.Items["Username"] = username;
                if (dict.TryGetValue("role", out var role)) context.Items["Role"] = role;
                if (dict.TryGetValue("loginAt", out var loginAt)) context.Items["LoginAt"] = loginAt;

                // 3. Sliding TTL: Gia hạn thêm 30 phút
                await db.KeyExpireAsync(sessionKey, TimeSpan.FromMinutes(30));

                // 4. Cập nhật thời điểm hoạt động
                await db.HashSetAsync(sessionKey, "lastActive", DateTime.UtcNow.ToString("O"));
            }
        }

        await _next(context);
    }
}
```

---

## 3. CurrentUserService CQRS & Phân Quyền

Controller không tự đọc Redis hay Cookie mà thông qua `ICurrentUserService.GetAsync(HttpContext)`.
Nhờ `SessionAuthMiddleware` đã nạp sẵn `Role` vào `HttpContext.Items`, phương thức `GetAsync` đọc trực tiếp từ bộ nhớ in-memory (O(1)) mà không tốn thêm bất kỳ network round-trip nào tới Redis hay MongoDB.
