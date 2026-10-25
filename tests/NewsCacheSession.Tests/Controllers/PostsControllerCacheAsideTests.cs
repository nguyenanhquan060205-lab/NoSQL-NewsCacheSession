using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
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

    // MongoContext để null: các test này chỉ đi nhánh Redis, không chạm MongoDB hay kho ảnh.
    private PostsController CreateController() =>
        new(null!, _mockCache.Object, _mockCurrentUser.Object,
            Mock.Of<IImageStorageService>(), NullLogger<PostsController>.Instance);

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

        var controller = CreateController();
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

        // Một request HIT chỉ được tính đúng một lần, dù có đọc thêm key views
        _mockCache.Verify(c => c.RecordLookup(true), Times.Once);
        _mockCache.Verify(c => c.RecordLookup(false), Times.Never);
    }

    [Fact]
    public async Task GetById_WithInvalidObjectId_ShouldReturnBadRequest()
    {
        // Arrange
        var controller = CreateController();
        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };

        // Act
        var result = await controller.GetById("invalid-id") as BadRequestObjectResult;

        // Assert
        result.Should().NotBeNull();
    }

    [Fact]
    public async Task GetAll_WhenCacheHit_ShouldReturnFromCacheWithHitHeader()
    {
        // Arrange
        var pagedResponse = new PagedPostsResponse
        {
            Page = 1,
            PageSize = 10,
            TotalItems = 1,
            TotalPages = 1,
            Items = new List<PostResponse>
            {
                new() { Id = "507f1f77bcf86cd799439011", Title = "Post 1" }
            }
        };

        _mockCache.Setup(c => c.GetAsync("posts:ver")).ReturnsAsync("1");
        _mockCache.Setup(c => c.GetAsync("posts:cat:all:p1:v1"))
            .ReturnsAsync(JsonSerializer.Serialize(pagedResponse));

        var controller = CreateController();
        var httpContext = new DefaultHttpContext();
        controller.ControllerContext = new ControllerContext { HttpContext = httpContext };

        // Act
        var result = await controller.GetAll(page: 1, pageSize: 10) as OkObjectResult;

        // Assert
        result.Should().NotBeNull();
        httpContext.Response.Headers["X-Cache"].ToString().Should().Be("HIT");

        var response = result!.Value as PagedPostsResponse;
        response.Should().NotBeNull();
        response!.Items.Should().HaveCount(1);
        response.Items[0].Title.Should().Be("Post 1");
    }

    [Fact]
    public async Task GetAll_WhenVersionKeyMissing_ShouldReadVersionZeroKey()
    {
        // Arrange — posts:ver chưa tồn tại thì key danh sách phải mang v0,
        // để INCR đầu tiên (trả về 1) chuyển sang key mới
        var pagedResponse = new PagedPostsResponse { Page = 1, PageSize = 10, TotalItems = 0, TotalPages = 0 };
        _mockCache.Setup(c => c.GetAsync("posts:ver")).ReturnsAsync((string?)null);
        _mockCache.Setup(c => c.GetAsync("posts:cat:all:p1:v0"))
            .ReturnsAsync(JsonSerializer.Serialize(pagedResponse));

        var controller = CreateController();
        var httpContext = new DefaultHttpContext();
        controller.ControllerContext = new ControllerContext { HttpContext = httpContext };

        // Act
        var result = await controller.GetAll(page: 1, pageSize: 10) as OkObjectResult;

        // Assert
        result.Should().NotBeNull();
        httpContext.Response.Headers["X-Cache"].ToString().Should().Be("HIT");
        _mockCache.Verify(c => c.GetAsync("posts:cat:all:p1:v1"), Times.Never);
    }

    [Fact]
    public async Task GetAll_WhenCachedPageSizeDiffers_ShouldFallThroughToMongo()
    {
        // Arrange — bản cache là của pageSize=3, request hỏi pageSize=12
        var cachedPage = new PagedPostsResponse { Page = 1, PageSize = 3, TotalItems = 100, TotalPages = 34 };
        _mockCache.Setup(c => c.GetAsync("posts:ver")).ReturnsAsync("1");
        _mockCache.Setup(c => c.GetAsync("posts:cat:all:p1:v1"))
            .ReturnsAsync(JsonSerializer.Serialize(cachedPage));

        // MongoContext null: lệch pageSize phải rơi xuống nhánh đọc MongoDB chứ không trả bản cache
        var controller = CreateController();
        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };

        // Act
        var act = () => controller.GetAll(page: 1, pageSize: 12);

        // Assert
        await act.Should().ThrowAsync<NullReferenceException>();
    }

    [Fact]
    public async Task GetAll_WithInvalidCategoryId_ShouldReturnBadRequest()
    {
        // Arrange
        var controller = CreateController();
        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };

        // Act
        var result = await controller.GetAll(page: 1, pageSize: 10, categoryId: "invalid-cat") as BadRequestObjectResult;

        // Assert
        result.Should().NotBeNull();
    }
}
