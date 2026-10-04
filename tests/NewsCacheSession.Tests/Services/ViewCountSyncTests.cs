using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using NewsCacheSession.Api.Controllers;
using NewsCacheSession.Api.Services;
using StackExchange.Redis;
using Xunit;

namespace NewsCacheSession.Tests.Services;

public class ViewCountSyncTests
{
    private readonly Mock<ICacheService> _mockCache;
    private readonly Mock<ICurrentUserService> _mockCurrentUser;

    public ViewCountSyncTests()
    {
        _mockCache = new Mock<ICacheService>();
        _mockCurrentUser = new Mock<ICurrentUserService>();
    }

    [Fact]
    public async Task IncrementView_WithValidId_ShouldCallIncrementAndReturnNewCount()
    {
        // Arrange
        var postId = "507f1f77bcf86cd799439011";
        var controller = new PostsController(null!, _mockCache.Object, _mockCurrentUser.Object);
        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };

        _mockCache.Setup(c => c.IncrementAsync($"post:{postId}:views"))
            .ReturnsAsync(15);

        // Act
        var result = await controller.IncrementView(postId) as OkObjectResult;

        // Assert
        result.Should().NotBeNull();
        _mockCache.Verify(c => c.IncrementAsync($"post:{postId}:views"), Times.Once);
        _mockCache.Verify(c => c.MarkDirtyViewAsync(postId), Times.Once);
    }

    [Fact]
    public async Task IncrementView_WithInvalidId_ShouldReturnBadRequest()
    {
        // Arrange
        var controller = new PostsController(null!, _mockCache.Object, _mockCurrentUser.Object);

        // Act
        var result = await controller.IncrementView("invalid-id") as BadRequestObjectResult;

        // Assert
        result.Should().NotBeNull();
        _mockCache.Verify(c => c.IncrementAsync(It.IsAny<string>()), Times.Never);
    }
}
