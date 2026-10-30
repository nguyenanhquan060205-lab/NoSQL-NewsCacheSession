using System.Net;
using FluentAssertions;
using MongoDB.Driver;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Tests.Integration.Infrastructure;

namespace NewsCacheSession.Tests.Integration;

/// <summary>
/// Bộ đếm lượt xem <c>post:{id}:views</c> (INCR) và worker Write-Behind flush về MongoDB.
/// </summary>
[Collection(IntegrationCollection.Name)]
public class ViewCounterFlowTests : IAsyncLifetime
{
    private readonly NewsApiFactory _factory;

    public ViewCounterFlowTests(NewsApiFactory factory) => _factory = factory;

    public Task InitializeAsync() => _factory.ResetAsync();
    public Task DisposeAsync() => Task.CompletedTask;

    private static async Task<long> ViewAsync(HttpClient client, string postId)
    {
        var response = await client.PostAsync($"/api/posts/{postId}/view", null);
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        return (await NewsApiFactory.ReadJsonAsync(response)).GetProperty("views").GetInt64();
    }

    private async Task<int> MongoViewsAsync(string postId) =>
        (await _factory.Posts.Find(p => p.Id == postId).SingleAsync()).Views;

    [IntegrationFact]
    public async Task IncrementView_FirstViewOfPostWithMongoViews_ShouldContinueFromMongoValue()
    {
        var post = await _factory.SeedPostAsync("Bài 500 lượt xem", views: 500);

        var views = await ViewAsync(_factory.CreateClient(), post.Id);

        views.Should().Be(501);
    }

    [IntegrationFact]
    public async Task IncrementView_FiftyParallelViews_ShouldCountEveryOne()
    {
        var post = await _factory.SeedPostAsync("Bài đông người xem", views: 10);
        var client = _factory.CreateClient();

        await Task.WhenAll(Enumerable.Range(0, 50).Select(_ => client.PostAsync($"/api/posts/{post.Id}/view", null)));

        ((long)await _factory.Redis.StringGetAsync($"post:{post.Id}:views")).Should().Be(60);
    }

    [IntegrationFact]
    public async Task IncrementView_UnknownId_ShouldReturn404AndNotCreateCounter()
    {
        var unknownId = MongoDB.Bson.ObjectId.GenerateNewId().ToString();

        var response = await _factory.CreateClient().PostAsync($"/api/posts/{unknownId}/view", null);

        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
        (await _factory.Redis.KeyExistsAsync($"post:{unknownId}:views")).Should().BeFalse();
    }

    [IntegrationFact]
    public async Task Flush_ShouldWriteRedisCounterToMongoAndEmptyDirtySet()
    {
        var post = await _factory.SeedPostAsync("Bài cần flush", views: 3);
        var client = _factory.CreateClient();
        for (var i = 0; i < 4; i++) await ViewAsync(client, post.Id);

        await _factory.ViewWorker.FlushViewsToMongoAsync(CancellationToken.None);

        (await MongoViewsAsync(post.Id)).Should().Be(7);
        (await _factory.Redis.SetLengthAsync("posts:dirty_views")).Should().Be(0);
    }

    [IntegrationFact]
    public async Task IncrementView_AfterRedisLostAllKeys_ShouldContinueFromFlushedMongoValue()
    {
        var post = await _factory.SeedPostAsync("Bài qua sự cố Redis", views: 100);
        var client = _factory.CreateClient();
        for (var i = 0; i < 3; i++) await ViewAsync(client, post.Id);
        await _factory.ViewWorker.FlushViewsToMongoAsync(CancellationToken.None);

        await _factory.Redis.ExecuteAsync("FLUSHDB"); // giả lập Redis khởi động lại không lưu đĩa
        var views = await ViewAsync(client, post.Id);
        await _factory.ViewWorker.FlushViewsToMongoAsync(CancellationToken.None);

        views.Should().Be(104);
        (await MongoViewsAsync(post.Id)).Should().Be(104, "lượt xem trong MongoDB không được tụt về số nhỏ");
    }

    [IntegrationFact]
    public async Task IncrementView_SoftDeletedPostWithLiveCounter_StillCounts()
    {
        // Hành vi đã biết, nhóm chấp nhận: kiểm tra "bài còn tồn tại" chỉ chạy ở lượt xem đầu tiên
        // để mọi lượt sau chỉ tốn một INCR. Test này ghi lại hành vi để phản biện, không phải mục tiêu.
        var post = await _factory.SeedPostAsync("Bài xem rồi bị xóa");
        var client = _factory.CreateClient();
        await ViewAsync(client, post.Id);
        await _factory.Posts.UpdateOneAsync(p => p.Id == post.Id, Builders<Post>.Update.Set(p => p.IsDeleted, true));

        var response = await client.PostAsync($"/api/posts/{post.Id}/view", null);

        response.StatusCode.Should().Be(HttpStatusCode.OK);
    }

    [IntegrationFact]
    public async Task CacheStats_AfterOneMissAndOneHit_ShouldCountEachOnce()
    {
        var post = await _factory.SeedPostAsync("Bài thống kê");
        var client = _factory.CreateClient();

        await client.GetAsync($"/api/posts/{post.Id}");
        await client.GetAsync($"/api/posts/{post.Id}");
        var stats = await NewsApiFactory.ReadJsonAsync(await client.GetAsync("/api/cache/stats"));

        stats.GetProperty("hits").GetInt64().Should().Be(1);
        stats.GetProperty("misses").GetInt64().Should().Be(1);
        stats.GetProperty("hitRate").GetDouble().Should().Be(50);
    }
}
