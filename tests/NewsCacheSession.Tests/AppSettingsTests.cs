using FluentAssertions;
using Microsoft.Extensions.Configuration;
using MongoDB.Driver;
using Xunit;

namespace NewsCacheSession.Tests;

public class AppSettingsTests
{
    private static IConfiguration LoadApiSettings()
    {
        // Đi ngược từ thư mục bin của test lên gốc repo để đọc đúng file cấu hình của API.
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "src", "NewsCacheSession.Api", "appsettings.json")))
            dir = dir.Parent;
        dir.Should().NotBeNull("phải tìm thấy src/NewsCacheSession.Api/appsettings.json");

        return new ConfigurationBuilder()
            .AddJsonFile(Path.Combine(dir!.FullName, "src", "NewsCacheSession.Api", "appsettings.json"))
            .Build();
    }

    [Fact]
    public void MongoConnectionString_ShouldFailFastWhenMongoIsDown()
    {
        // Mặc định driver chờ chọn server 30 giây: MongoDB sập thì mọi request chưa có cache treo 30 giây
        // rồi mới 500 (đo được ở kịch bản độ bền).
        var url = MongoUrl.Create(LoadApiSettings()["MongoSettings:ConnectionString"]);

        url.ServerSelectionTimeout.Should().Be(TimeSpan.FromSeconds(5));
        url.Server.Port.Should().Be(27017, "vẫn trỏ vào container theo docker-compose.yml");
    }
}
