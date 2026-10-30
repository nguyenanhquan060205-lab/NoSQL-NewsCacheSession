using FluentAssertions;
using Microsoft.Extensions.Options;
using NewsCacheSession.Api.Services;
using Xunit;

namespace NewsCacheSession.Tests.Services;

public class CloudinaryImageStorageServiceTests
{
    [Fact]
    public void Constructor_ShouldCapHttpTimeoutAt15Seconds()
    {
        // HttpClient mặc định chờ 100 giây: Cloudinary treo thì request sửa/xóa bài treo theo.
        var httpClient = new HttpClient();

        _ = new CloudinaryImageStorageService(httpClient, Options.Create(new CloudinarySettings()));

        httpClient.Timeout.Should().Be(TimeSpan.FromSeconds(15));
    }
}
