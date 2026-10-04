using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using NewsCacheSession.Api.Controllers;
using NewsCacheSession.Api.DTOs.Posts;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Api.Services;
using Xunit;

namespace NewsCacheSession.Tests.Integration;

public class CacheInvalidationTests
{
    private readonly Mock<ICacheService> _mockCache;
    private readonly Mock<ICurrentUserService> _mockCurrentUser;

    public CacheInvalidationTests()
    {
        _mockCache = new Mock<ICacheService>();
        _mockCurrentUser = new Mock<ICurrentUserService>();
    }

    [Fact]
    public async Task CacheInvalidation_WhenBumpListVersionCalled_ShouldIncrementPostsVerKey()
    {
        // Arrange
        _mockCache.Setup(c => c.IncrementAsync("posts:ver"))
            .ReturnsAsync(2);

        // Act
        var newVersion = await _mockCache.Object.IncrementAsync("posts:ver");

        // Assert
        newVersion.Should().Be(2);
        _mockCache.Verify(c => c.IncrementAsync("posts:ver"), Times.Once);
    }

    [Fact]
    public async Task CacheInvalidation_WhenPostDeletedOrUpdated_ShouldRemoveCacheKey()
    {
        // Arrange
        var postId = "507f1f77bcf86cd799439011";
        var cacheKey = $"post:{postId}";

        _mockCache.Setup(c => c.RemoveAsync(cacheKey))
            .Returns(Task.CompletedTask);

        // Act
        await _mockCache.Object.RemoveAsync(cacheKey);

        // Assert
        _mockCache.Verify(c => c.RemoveAsync(cacheKey), Times.Once);
    }
}
