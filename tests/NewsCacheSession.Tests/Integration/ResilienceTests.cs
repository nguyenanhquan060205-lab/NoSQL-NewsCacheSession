using System.Diagnostics;
using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using MongoDB.Driver;
using NewsCacheSession.Api.Services;
using NewsCacheSession.Tests.Integration.Infrastructure;

namespace NewsCacheSession.Tests.Integration;

/// <summary>
/// Hành vi khi Redis, MongoDB hoặc Cloudinary gặp sự cố. Redis/Mongo "sập" được giả lập bằng
/// cách trỏ factory riêng vào một cổng không có gì lắng nghe — không đụng container nào.
/// </summary>
[Collection(IntegrationCollection.Name)]
public class ResilienceTests : IAsyncLifetime
{
    private const string DeadRedis = "localhost:6399";
    private const string DeadMongo = "mongodb://localhost:27999/?serverSelectionTimeoutMS=500&connectTimeoutMS=500";

    private readonly NewsApiFactory _factory;

    public ResilienceTests(NewsApiFactory factory) => _factory = factory;

    public Task InitializeAsync() => _factory.ResetAsync();
    public Task DisposeAsync() => Task.CompletedTask;

    [IntegrationFact]
    public async Task RedisDown_PublicReadsServeFromMongo_SessionActionsReturn503_HealthUnhealthy()
    {
        var post = await _factory.SeedPostAsync("Đọc được khi Redis sập");
        // Cùng DB Mongo với factory chính để thấy bài vừa seed.
        await using var down = new NewsApiFactory(mongoUri: null, redisEndpoint: DeadRedis, sessionTtlMinutes: null,
            databaseName: _factory.DatabaseName);
        var client = down.CreateClient();
        client.DefaultRequestHeaders.Add("Cookie", "SessionId=phien-bat-ky");

        var password = NewsApiFactory.NewPassword();

        var watch = Stopwatch.StartNew();
        var list = await client.GetAsync("/api/posts");
        var detail = await client.GetAsync($"/api/posts/{post.Id}");
        var readsElapsed = watch.Elapsed;
        var create = await client.PostAsJsonAsync("/api/posts", new { title = "Không tạo được", content = "x" });
        var register = await NewsApiFactory.RegisterAsync(client, "dang_ky_khi_redis_sap", password);
        var login = await client.PostAsJsonAsync("/api/auth/login", new { username = "dang_ky_khi_redis_sap", password });
        var health = await client.GetAsync("/health");

        list.StatusCode.Should().Be(HttpStatusCode.OK, "trang chủ vẫn đọc được từ MongoDB");
        detail.StatusCode.Should().Be(HttpStatusCode.OK, "trang chi tiết vẫn đọc được từ MongoDB");
        NewsApiFactory.CacheHeader(detail).Should().Be("MISS");
        readsElapsed.Should().BeLessThan(TimeSpan.FromSeconds(1), "không được treo chờ Redis tới hết timeout");
        create.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable, "thao tác cần phiên phải báo rõ Redis không sẵn sàng");
        register.StatusCode.Should().Be(HttpStatusCode.Created, "đăng ký chỉ ghi MongoDB");
        login.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable, "không tạo được phiên khi Redis sập");
        (await NewsApiFactory.ReadJsonAsync(login)).GetProperty("message").GetString().Should().Contain("Redis");
        health.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable);
    }

    [IntegrationFact]
    public async Task GetById_WhileAnotherHolderKeepsLock_ShouldFallBackToMongoWithinBoundedWait()
    {
        var post = await _factory.SeedPostAsync("Bài bị giữ khóa");
        // Lock do một tiến trình đã chết để lại: chỉ tự hết sau 5 giây.
        await _factory.Redis.StringSetAsync($"lock:post:{post.Id}", "tien-trinh-da-chet", TimeSpan.FromSeconds(5));
        var client = _factory.CreateClient();

        var watch = Stopwatch.StartNew();
        var response = await client.GetAsync($"/api/posts/{post.Id}");
        watch.Stop();

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        (await NewsApiFactory.ReadJsonAsync(response)).GetProperty("title").GetString().Should().Be("Bài bị giữ khóa");
        watch.Elapsed.Should().BeLessThan(TimeSpan.FromSeconds(3.5),
            "chờ lock phải có giới hạn rồi đọc thẳng MongoDB, không đợi tới khi lock tự hết hạn");
    }

    [IntegrationFact]
    public async Task Update_WhileCloudinaryIsSlow_ShouldInvalidateCacheBeforeDeletingOldImage()
    {
        var post = await _factory.SeedPostAsync("Bài có ảnh", imagePublicId: "posts/anh-cu");
        var slowStorage = new SlowImageStorage(TimeSpan.FromSeconds(3));
        await using var app = _factory.WithWebHostBuilder(b =>
            b.ConfigureTestServices(s => s.AddSingleton<IImageStorageService>(slowStorage)));
        var (admin, _, _) = await NewsApiFactory.SignInOnAsync(app, "admin_dau_tien");
        await admin.GetAsync($"/api/posts/{post.Id}");
        (await _factory.Redis.KeyExistsAsync($"post:{post.Id}")).Should().BeTrue();

        var put = admin.PutAsJsonAsync($"/api/posts/{post.Id}",
            new { title = "Bài có ảnh mới", content = "x", imagePublicId = "posts/anh-moi" });
        await slowStorage.DeleteStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));
        var cacheAliveDuringCloudinaryCall = await _factory.Redis.KeyExistsAsync($"post:{post.Id}");
        (await put).StatusCode.Should().Be(HttpStatusCode.OK);

        slowStorage.DeletedPublicIds.Should().ContainSingle().Which.Should().Be("posts/anh-cu");
        cacheAliveDuringCloudinaryCall.Should().BeFalse(
            "MongoDB đã ghi xong thì phải xóa cache ngay, không để bản cũ sống trong lúc chờ Cloudinary");
    }

    [IntegrationFact]
    public async Task Flush_WhenMongoWriteFails_ShouldKeepPostIdDirtyForNextRound()
    {
        var postId = MongoDB.Bson.ObjectId.GenerateNewId().ToString();
        await _factory.Redis.StringSetAsync($"post:{postId}:views", 42);
        await _factory.Redis.SetAddAsync("posts:dirty_views", postId);
        await using var mongoDown = new NewsApiFactory(mongoUri: DeadMongo, redisEndpoint: null, sessionTtlMinutes: null);

        try
        {
            await mongoDown.ViewWorker.FlushViewsToMongoAsync(CancellationToken.None);
        }
        catch (Exception)
        {
            // Hành vi cũ ném lỗi ra ngoài; điều cần kiểm tra là ID còn trong Set hay không.
        }

        (await _factory.Redis.SetContainsAsync("posts:dirty_views", postId)).Should().BeTrue(
            "ghi MongoDB lỗi thì lượt flush sau phải thử lại, không được mất dấu bài viết");
    }

    /// <summary>Kho ảnh giả: xóa ảnh mất <paramref name="delay"/> như khi Cloudinary phản hồi chậm.</summary>
    private sealed class SlowImageStorage(TimeSpan delay) : IImageStorageService
    {
        public TaskCompletionSource DeleteStarted { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public List<string> DeletedPublicIds { get; } = new();

        public Task<UploadedImage> UploadAsync(IFormFile file, CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();

        public async Task DeleteAsync(string publicId, CancellationToken cancellationToken = default)
        {
            DeleteStarted.TrySetResult();
            await Task.Delay(delay, cancellationToken);
            DeletedPublicIds.Add(publicId);
        }
    }
}
