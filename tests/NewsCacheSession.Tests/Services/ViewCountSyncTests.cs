using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
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

    // MongoContext để null: các test này chỉ đi nhánh Redis, không chạm MongoDB hay kho ảnh.
    private PostsController CreateController() =>
        new(null!, _mockCache.Object, _mockCurrentUser.Object,
            Mock.Of<IImageStorageService>(), NullLogger<PostsController>.Instance);

    [Fact]
    public async Task IncrementView_WithValidId_ShouldCallIncrementAndReturnNewCount()
    {
        // Arrange
        var postId = "507f1f77bcf86cd799439011";
        var controller = CreateController();
        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };

        // Key đếm đã tồn tại nên không cần tra MongoDB (MongoContext để null)
        _mockCache.Setup(c => c.GetAsync($"post:{postId}:views"))
            .ReturnsAsync("14");
        _mockCache.Setup(c => c.IncrementAsync($"post:{postId}:views"))
            .ReturnsAsync(15);

        // Act
        var result = await controller.IncrementView(postId) as OkObjectResult;

        // Assert
        result.Should().NotBeNull();
        _mockCache.Verify(c => c.IncrementAsync($"post:{postId}:views"), Times.Once);
        _mockCache.Verify(c => c.MarkDirtyViewAsync(postId), Times.Once);

        // Bộ đếm đang chạy thì không được khởi tạo lại từ posts.views
        _mockCache.Verify(c => c.SetIfNotExistsAsync(It.IsAny<string>(), It.IsAny<string>()), Times.Never);
    }

    [Fact]
    public async Task IncrementView_WithInvalidId_ShouldReturnBadRequest()
    {
        // Arrange
        var controller = CreateController();

        // Act
        var result = await controller.IncrementView("invalid-id") as BadRequestObjectResult;

        // Assert
        result.Should().NotBeNull();
        _mockCache.Verify(c => c.IncrementAsync(It.IsAny<string>()), Times.Never);
    }
}
