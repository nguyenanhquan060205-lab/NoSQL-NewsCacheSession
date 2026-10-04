using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Moq;
using NewsCacheSession.Api.Middleware;
using NewsCacheSession.Api.Services;
using Xunit;

namespace NewsCacheSession.Tests.Middleware;

public class SessionAuthMiddlewareTests
{
    private readonly Mock<ISessionService> _mockSessionService;
    private readonly IConfiguration _config;
    private bool _nextCalled;

    public SessionAuthMiddlewareTests()
    {
        _mockSessionService = new Mock<ISessionService>();
        _config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["SessionSettings:TtlMinutes"] = "30"
            })
            .Build();
        _nextCalled = false;
    }

    private Task NextDelegate(HttpContext ctx)
    {
        _nextCalled = true;
        return Task.CompletedTask;
    }

    [Fact]
    public async Task InvokeAsync_WithValidCookieSession_ShouldPopulateItemsAndRefreshTtl()
    {
        // Arrange
        var middleware = new SessionAuthMiddleware(NextDelegate);
        var context = new DefaultHttpContext();
        context.Request.Headers["Cookie"] = "SessionId=valid-sess-123";

        var sessionData = new Dictionary<string, string>
        {
            ["userId"] = "user-1",
            ["username"] = "john_doe",
            ["role"] = "admin",
            ["loginAt"] = "1700000000"
        };

        _mockSessionService.Setup(s => s.GetSessionAsync("valid-sess-123"))
            .ReturnsAsync(sessionData);

        // Act
        await middleware.InvokeAsync(context, _mockSessionService.Object, _config);

        // Assert
        _nextCalled.Should().BeTrue();
        context.Items["UserId"].Should().Be("user-1");
        context.Items["Username"].Should().Be("john_doe");
        context.Items["Role"].Should().Be("admin");
        context.Items["LoginAt"].Should().Be("1700000000");

        _mockSessionService.Verify(s => s.RefreshSessionAsync("valid-sess-123", TimeSpan.FromMinutes(30)), Times.Once);
    }

    [Fact]
    public async Task InvokeAsync_WithValidHeaderSession_ShouldPopulateItems()
    {
        // Arrange
        var middleware = new SessionAuthMiddleware(NextDelegate);
        var context = new DefaultHttpContext();
        context.Request.Headers["X-Session-Id"] = "header-sess-456";

        var sessionData = new Dictionary<string, string>
        {
            ["userId"] = "user-2",
            ["username"] = "jane_doe",
            ["role"] = "user",
            ["loginAt"] = "1700000000"
        };

        _mockSessionService.Setup(s => s.GetSessionAsync("header-sess-456"))
            .ReturnsAsync(sessionData);

        // Act
        await middleware.InvokeAsync(context, _mockSessionService.Object, _config);

        // Assert
        _nextCalled.Should().BeTrue();
        context.Items["UserId"].Should().Be("user-2");
        context.Items["Role"].Should().Be("user");
        _mockSessionService.Verify(s => s.RefreshSessionAsync("header-sess-456", TimeSpan.FromMinutes(30)), Times.Once);
    }

    [Fact]
    public async Task InvokeAsync_WithoutSession_ShouldContinueWithoutPopulatingItems()
    {
        // Arrange
        var middleware = new SessionAuthMiddleware(NextDelegate);
        var context = new DefaultHttpContext();

        // Act
        await middleware.InvokeAsync(context, _mockSessionService.Object, _config);

        // Assert
        _nextCalled.Should().BeTrue();
        context.Items.Should().NotContainKey("UserId");
        _mockSessionService.Verify(s => s.RefreshSessionAsync(It.IsAny<string>(), It.IsAny<TimeSpan>()), Times.Never);
    }
}
