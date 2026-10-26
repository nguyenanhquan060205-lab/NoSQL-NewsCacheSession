using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using NewsCacheSession.Tests.Integration.Infrastructure;
using StackExchange.Redis;

namespace NewsCacheSession.Tests.Integration;

/// <summary>
/// Cache-Aside ở <c>GET /api/posts/{id}</c> và cache danh sách, kiểm tra trực tiếp trên Redis thật:
/// key có đúng kiểu/TTL không, sửa/xóa bài có xóa cache ngay không.
/// </summary>
[Collection(IntegrationCollection.Name)]
public class CacheInvalidationTests : IAsyncLifetime
{
    private readonly NewsApiFactory _factory;

    public CacheInvalidationTests(NewsApiFactory factory) => _factory = factory;

    public Task InitializeAsync() => _factory.ResetAsync();
    public Task DisposeAsync() => Task.CompletedTask;

    private static object Edit(string title) => new { title, content = "Nội dung đã sửa" };

    [IntegrationFact]
    public async Task GetById_FirstThenSecondCall_ShouldMissThenHitAndStoreStringWithTtl()
    {
        var post = await _factory.SeedPostAsync("Bài kiểm tra cache");
        var client = _factory.CreateClient();

        var first = await client.GetAsync($"/api/posts/{post.Id}");
        var second = await client.GetAsync($"/api/posts/{post.Id}");

        NewsApiFactory.CacheHeader(first).Should().Be("MISS");
        NewsApiFactory.CacheHeader(second).Should().Be("HIT");
        (await _factory.Redis.KeyTypeAsync($"post:{post.Id}")).Should().Be(RedisType.String);
        var ttl = await _factory.Redis.KeyTimeToLiveAsync($"post:{post.Id}");
        ttl.Should().NotBeNull();
        ttl!.Value.TotalSeconds.Should().BeInRange(1, 600);
    }

    [IntegrationFact]
    public async Task Update_ShouldDeleteCacheKeyBumpListVersionAndNextGetMissesWithNewTitle()
    {
        var post = await _factory.SeedPostAsync("Tiêu đề cũ");
        var (admin, _, _) = await _factory.SignInNewUserAsync("admin_dau_tien");
        await admin.GetAsync($"/api/posts/{post.Id}");
        (await _factory.Redis.KeyExistsAsync($"post:{post.Id}")).Should().BeTrue();
        var verBefore = (long?)await _factory.Redis.StringGetAsync("posts:ver") ?? 0;

        var update = await admin.PutAsJsonAsync($"/api/posts/{post.Id}", Edit("Tiêu đề mới"));

        update.StatusCode.Should().Be(HttpStatusCode.OK);
        (await _factory.Redis.KeyExistsAsync($"post:{post.Id}")).Should().BeFalse("PUT xong là cache cũ phải biến mất ngay");
        ((long)await _factory.Redis.StringGetAsync("posts:ver")).Should().Be(verBefore + 1);

        var after = await admin.GetAsync($"/api/posts/{post.Id}");
        NewsApiFactory.CacheHeader(after).Should().Be("MISS");
        (await NewsApiFactory.ReadJsonAsync(after)).GetProperty("title").GetString().Should().Be("Tiêu đề mới");
    }

    [IntegrationFact]
    public async Task Delete_ShouldDeleteCacheKeyButKeepViewCounter()
    {
        var post = await _factory.SeedPostAsync("Bài sắp xóa", views: 7);
        var (admin, _, _) = await _factory.SignInNewUserAsync("admin_dau_tien");
        await admin.GetAsync($"/api/posts/{post.Id}");
        await admin.PostAsync($"/api/posts/{post.Id}/view", null);

        var delete = await admin.DeleteAsync($"/api/posts/{post.Id}");

        delete.StatusCode.Should().Be(HttpStatusCode.NoContent);
        (await _factory.Redis.KeyExistsAsync($"post:{post.Id}")).Should().BeFalse();
        ((long)await _factory.Redis.StringGetAsync($"post:{post.Id}:views")).Should().Be(8,
            "xóa mềm giữ bộ đếm để worker còn chốt lượt xem về MongoDB");
    }

    [IntegrationFact]
    public async Task GetBySlug_ShouldNotCreateAnyPostCacheKey()
    {
        var post = await _factory.SeedPostAsync("Bài theo slug");

        var response = await _factory.CreateClient().GetAsync($"/api/posts/slug/{post.Slug}");

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        _factory.RedisKeys("post:*").Should().BeEmpty("endpoint slug cố ý không cache");
    }

    [IntegrationFact]
    public async Task GetAll_HitAfterFirstCall_ThenMissWithNewPostFirstAfterCreate()
    {
        await _factory.SeedPostAsync("Bài cũ", createdAt: DateTime.UtcNow.AddHours(-1));
        var (admin, _, _) = await _factory.SignInNewUserAsync("admin_dau_tien");

        var first = await admin.GetAsync("/api/posts?page=1&pageSize=10");
        var second = await admin.GetAsync("/api/posts?page=1&pageSize=10");
        await admin.PostAsJsonAsync("/api/posts", new { title = "Bài mới đăng", content = "Nội dung" });
        var third = await admin.GetAsync("/api/posts?page=1&pageSize=10");

        NewsApiFactory.CacheHeader(first).Should().Be("MISS");
        NewsApiFactory.CacheHeader(second).Should().Be("HIT");
        NewsApiFactory.CacheHeader(third).Should().Be("MISS");
        (await NewsApiFactory.ReadJsonAsync(third)).GetProperty("items")[0].GetProperty("title").GetString()
            .Should().Be("Bài mới đăng");
        _factory.RedisKeys("posts:cat:all:p1:v*").Should().HaveCount(2, "mỗi phiên bản danh sách một key riêng");
    }

    [IntegrationFact]
    public async Task GetById_FiftyParallelRequestsOnColdKey_ShouldMissExactlyOnceAndReleaseLock()
    {
        var post = await _factory.SeedPostAsync("Bài bị dồn request");
        var client = _factory.CreateClient();

        var responses = await Task.WhenAll(Enumerable.Range(0, 50).Select(_ => client.GetAsync($"/api/posts/{post.Id}")));

        responses.Should().OnlyContain(r => r.StatusCode == HttpStatusCode.OK);
        var headers = responses.Select(NewsApiFactory.CacheHeader).ToList();
        headers.Count(h => h == "MISS").Should().Be(1, "lock chống stampede chỉ cho một request đọc MongoDB");
        headers.Count(h => h == "HIT").Should().Be(49);
        (await _factory.Redis.KeyExistsAsync($"lock:post:{post.Id}")).Should().BeFalse();
    }
}
