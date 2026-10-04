using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Moq;
using NewsCacheSession.Api.Middleware;
using NewsCacheSession.Api.Services;
using Xunit;

namespace NewsCacheSession.Tests.Integration;

public class SessionExpiryTests
{
    private readonly Mock<ISessionService> _mockSession;
    private readonly IConfiguration _config;

    public SessionExpiryTests()
    {
        _mockSession = new Mock<ISessionService>();
        _config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["SessionSettings:TtlMinutes"] = "30"
            })
            .Build();
    }

    [Fact]
    public async Task SessionExpiry_WhenSessionExpiredInRedis_ShouldNotPopulateContextItems()
    {
        // Arrange
        var middleware = new SessionAuthMiddleware(_ => Task.CompletedTask);
        var context = new DefaultHttpContext();
        context.Request.Headers["X-Session-Id"] = "expired-session-id";

        // Redis trả về null vì key đã hết hạn theo TTL
        _mockSession.Setup(s => s.GetSessionAsync("expired-session-id"))
            .ReturnsAsync((Dictionary<string, string>?)null);

        // Act
        await middleware.InvokeAsync(context, _mockSession.Object, _config);

        // Assert
        context.Items.Should().NotContainKey("UserId");
        context.Items.Should().NotContainKey("Role");
        _mockSession.Verify(s => s.RefreshSessionAsync(It.IsAny<string>(), It.IsAny<TimeSpan>()), Times.Never);
    }

    [Fact]
    public async Task SessionSliding_WhenActiveUserSendsRequest_ShouldExtendTtlBy30Minutes()
    {
        // Arrange
        var middleware = new SessionAuthMiddleware(_ => Task.CompletedTask);
        var context = new DefaultHttpContext();
        context.Request.Headers["X-Session-Id"] = "active-session-id";

        var sessionData = new Dictionary<string, string>
        {
            ["userId"] = "user-123",
            ["username"] = "active_user",
            ["role"] = "user",
            ["loginAt"] = "1700000000"
        };

        _mockSession.Setup(s => s.GetSessionAsync("active-session-id"))
            .ReturnsAsync(sessionData);

        // Act
        await middleware.InvokeAsync(context, _mockSession.Object, _config);

        // Assert
        context.Items["UserId"].Should().Be("user-123");
        // Kiểm tra sliding expiration gia hạn thêm đúng 30 phút
        _mockSession.Verify(s => s.RefreshSessionAsync("active-session-id", TimeSpan.FromMinutes(30)), Times.Once);
    }
}
