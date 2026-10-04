using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using NewsCacheSession.Api.Controllers;
using NewsCacheSession.Api.DTOs.Posts;
using NewsCacheSession.Api.Services;
using Xunit;

namespace NewsCacheSession.Tests.Controllers;

public class PostsControllerCacheAsideTests
{
    private readonly Mock<ICacheService> _mockCache;
    private readonly Mock<ICurrentUserService> _mockCurrentUser;

    public PostsControllerCacheAsideTests()
    {
        _mockCache = new Mock<ICacheService>();
        _mockCurrentUser = new Mock<ICurrentUserService>();
    }

    [Fact]
    public async Task GetById_WhenCacheHit_ShouldReturnFromCacheWithHitHeaderAndNotQueryMongo()
    {
        // Arrange
        var postId = "507f1f77bcf86cd799439011";
        var cachedPost = new PostResponse
        {
            Id = postId,
            Title = "Cached Title",
            Content = "Cached Content",
            Views = 10
        };

        _mockCache.Setup(c => c.GetAsync($"post:{postId}"))
            .ReturnsAsync(JsonSerializer.Serialize(cachedPost));
        _mockCache.Setup(c => c.GetAsync($"post:{postId}:views"))
            .ReturnsAsync("25"); // Overridden views

        var controller = new PostsController(null!, _mockCache.Object, _mockCurrentUser.Object);
        var httpContext = new DefaultHttpContext();
        controller.ControllerContext = new ControllerContext { HttpContext = httpContext };

        // Act
        var result = await controller.GetById(postId) as OkObjectResult;

        // Assert
        result.Should().NotBeNull();
        httpContext.Response.Headers["X-Cache"].ToString().Should().Be("HIT");

        var response = result!.Value as PostResponse;
        response.Should().NotBeNull();
        response!.Title.Should().Be("Cached Title");
        response.Views.Should().Be(25); // Views was overridden by realtime counter
    }

    [Fact]
    public async Task GetById_WithInvalidObjectId_ShouldReturnBadRequest()
    {
        // Arrange
        var controller = new PostsController(null!, _mockCache.Object, _mockCurrentUser.Object);
        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };

        // Act
        var result = await controller.GetById("invalid-id") as BadRequestObjectResult;

        // Assert
        result.Should().NotBeNull();
    }
}
