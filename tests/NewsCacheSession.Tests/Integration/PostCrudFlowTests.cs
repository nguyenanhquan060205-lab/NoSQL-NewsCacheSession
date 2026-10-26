using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using Microsoft.Extensions.Configuration;
using MongoDB.Bson;
using MongoDB.Driver;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Tests.Integration.Infrastructure;

namespace NewsCacheSession.Tests.Integration;

/// <summary>
/// CRUD bài viết + phân quyền của SV1 đi qua HTTP thật tới MongoDB + Redis thật.
/// </summary>
[Collection(IntegrationCollection.Name)]
public class PostCrudFlowTests : IAsyncLifetime
{
    private readonly NewsApiFactory _factory;

    public PostCrudFlowTests(NewsApiFactory factory) => _factory = factory;

    public Task InitializeAsync() => _factory.ResetAsync();
    public Task DisposeAsync() => Task.CompletedTask;

    private static object NewPost(string title, string? categoryId = null) =>
        new { title, content = "Nội dung kiểm thử", imageUrl = "https://picsum.photos/seed/it/800/450", categoryId };

    [IntegrationFact]
    public async Task Create_WithoutLogin_ShouldReturn401()
    {
        var response = await _factory.CreateClient().PostAsJsonAsync("/api/posts", NewPost("Không đăng nhập"));

        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        (await _factory.Posts.CountDocumentsAsync(FilterDefinition<Post>.Empty)).Should().Be(0);
    }

    [IntegrationFact]
    public async Task Create_WithValidCategory_ShouldStoreVietnameseSlugAndObjectIdReferences()
    {
        var category = await _factory.SeedCategoryAsync("Thời sự");
        var (admin, _, adminId) = await _factory.SignInNewUserAsync("tac_gia");

        var response = await admin.PostAsJsonAsync("/api/posts", NewPost("Đường phố Hà Nội mùa thu", category.Id));

        response.StatusCode.Should().Be(HttpStatusCode.Created);
        var body = await NewsApiFactory.ReadJsonAsync(response);
        body.GetProperty("slug").GetString().Should().Be("duong-pho-ha-noi-mua-thu");

        var raw = await _factory.RawPosts.Find(new BsonDocument("slug", "duong-pho-ha-noi-mua-thu")).SingleAsync();
        raw["categoryId"].BsonType.Should().Be(BsonType.ObjectId);
        raw["authorId"].BsonType.Should().Be(BsonType.ObjectId);
        raw["authorId"].AsObjectId.ToString().Should().Be(adminId);
        raw.Names.Should().Contain(new[] { "title", "content", "imageUrl", "isDeleted", "createdAt", "updatedAt", "views" });
    }

    [IntegrationFact]
    public async Task Create_WithMalformedOrUnknownCategory_ShouldReturn400()
    {
        var (admin, _, _) = await _factory.SignInNewUserAsync("tac_gia");

        var malformed = await admin.PostAsJsonAsync("/api/posts", NewPost("Sai cú pháp", "khong-phai-objectid"));
        var unknown = await admin.PostAsJsonAsync("/api/posts", NewPost("Không tồn tại", ObjectId.GenerateNewId().ToString()));

        malformed.StatusCode.Should().Be(HttpStatusCode.BadRequest);
        unknown.StatusCode.Should().Be(HttpStatusCode.BadRequest);
    }

    [IntegrationFact]
    public async Task Create_TwoPostsWithSameTitleSequentially_ShouldSuffixSecondSlug()
    {
        var (admin, _, _) = await _factory.SignInNewUserAsync("tac_gia");

        var first = await NewsApiFactory.ReadJsonAsync(await admin.PostAsJsonAsync("/api/posts", NewPost("Tin trùng tên")));
        var second = await NewsApiFactory.ReadJsonAsync(await admin.PostAsJsonAsync("/api/posts", NewPost("Tin trùng tên")));

        first.GetProperty("slug").GetString().Should().Be("tin-trung-ten");
        second.GetProperty("slug").GetString().Should().Be("tin-trung-ten-2");
    }

    [IntegrationFact]
    public async Task Create_TenParallelPostsWithSameTitle_ShouldNeverReturn500()
    {
        var (admin, _, _) = await _factory.SignInNewUserAsync("tac_gia");

        var responses = await Task.WhenAll(Enumerable.Range(1, 10)
            .Select(_ => admin.PostAsJsonAsync("/api/posts", NewPost("Tin chen nhau"))));

        var codes = responses.Select(r => (int)r.StatusCode).ToList();
        codes.Should().NotContain(500, "unique index ux_posts_slug chặn trùng slug, API phải xử lý thay vì trả 500");
        codes.Should().OnlyContain(c => c == 201 || c == 409);
        var created = await _factory.Posts.Find(p => p.Title == "Tin chen nhau").ToListAsync();
        created.Should().HaveCount(codes.Count(c => c == 201));
        created.Select(p => p.Slug).Should().OnlyHaveUniqueItems();
    }

    [IntegrationFact]
    public async Task CreateAndUpload_WhenPostingIsAdminOnly_RegularUser403_AdminAllowed()
    {
        // Bản deploy công khai đặt PostingSettings:AdminOnly=true để người lạ không đăng được link lừa đảo.
        await using var app = _factory.WithWebHostBuilder(b => b.ConfigureAppConfiguration((_, config) =>
            config.AddInMemoryCollection(new Dictionary<string, string?> { ["PostingSettings:AdminOnly"] = "true" })));
        var (admin, _, _) = await NewsApiFactory.SignInOnAsync(app, "admin_dau_tien");
        var (user, _, _) = await NewsApiFactory.SignInOnAsync(app, "nguoi_la");

        var userPost = await user.PostAsJsonAsync("/api/posts", NewPost("Bài của người lạ"));
        var userUpload = await user.PostAsync("/api/images", ImageForm());
        var adminPost = await admin.PostAsJsonAsync("/api/posts", NewPost("Bài của admin"));
        var adminUpload = await admin.PostAsync("/api/images", ImageForm());

        userPost.StatusCode.Should().Be(HttpStatusCode.Forbidden);
        (await NewsApiFactory.ReadJsonAsync(userPost)).GetProperty("message").GetString().Should().Contain("quản trị viên");
        userUpload.StatusCode.Should().Be(HttpStatusCode.Forbidden);
        adminPost.StatusCode.Should().Be(HttpStatusCode.Created);
        adminUpload.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable, "qua được cổng phân quyền, chỉ vướng Cloudinary chưa cấu hình");
        (await _factory.Posts.CountDocumentsAsync(p => p.Title == "Bài của người lạ")).Should().Be(0);
    }

    private static MultipartFormDataContent ImageForm()
    {
        var png = Convert.FromBase64String(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==");
        var file = new ByteArrayContent(png);
        file.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/png");
        return new MultipartFormDataContent { { file, "file", "a.png" } };
    }

    [IntegrationFact]
    public async Task Create_OverlongTitle_ShouldReturn400()
    {
        var (admin, _, _) = await _factory.SignInNewUserAsync("tac_gia");

        var response = await admin.PostAsJsonAsync("/api/posts", NewPost(new string('t', 301)));

        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
    }

    [IntegrationFact]
    public async Task UpdateAndDelete_SeedPostByRegularUser_ShouldReturn403AndKeepCache()
    {
        var seed = await _factory.SeedPostAsync("Bài seed không tác giả");
        await _factory.SignInNewUserAsync("admin_dau_tien"); // chiếm vai admin
        var (user, _, _) = await _factory.SignInNewUserAsync("nguoi_thuong");
        await user.GetAsync($"/api/posts/{seed.Id}"); // nạp cache

        var update = await user.PutAsJsonAsync($"/api/posts/{seed.Id}", NewPost("Bị sửa trộm"));
        var delete = await user.DeleteAsync($"/api/posts/{seed.Id}");

        update.StatusCode.Should().Be(HttpStatusCode.Forbidden);
        delete.StatusCode.Should().Be(HttpStatusCode.Forbidden);
        (await _factory.Redis.KeyExistsAsync($"post:{seed.Id}")).Should().BeTrue("từ chối thì không được xóa cache");
        (await _factory.Posts.Find(p => p.Id == seed.Id).SingleAsync()).Title.Should().Be("Bài seed không tác giả");
    }

    [IntegrationFact]
    public async Task Update_AuthorEditsOwnPost_AndAdminEditsAnyPost_ShouldReturn200()
    {
        var seed = await _factory.SeedPostAsync("Bài seed");
        var (admin, _, _) = await _factory.SignInNewUserAsync("admin_dau_tien");
        var (author, _, _) = await _factory.SignInNewUserAsync("tac_gia");
        var own = await NewsApiFactory.ReadJsonAsync(await author.PostAsJsonAsync("/api/posts", NewPost("Bài của tôi")));
        var ownId = own.GetProperty("id").GetString();

        var authorEdit = await author.PutAsJsonAsync($"/api/posts/{ownId}", NewPost("Bài của tôi (đã sửa)"));
        var adminEditSeed = await admin.PutAsJsonAsync($"/api/posts/{seed.Id}", NewPost("Admin sửa bài seed"));
        var adminEditOther = await admin.PutAsJsonAsync($"/api/posts/{ownId}", NewPost("Admin sửa bài người khác"));

        authorEdit.StatusCode.Should().Be(HttpStatusCode.OK);
        adminEditSeed.StatusCode.Should().Be(HttpStatusCode.OK);
        adminEditOther.StatusCode.Should().Be(HttpStatusCode.OK);
        (await _factory.Posts.Find(p => p.Id == seed.Id).SingleAsync()).Title.Should().Be("Admin sửa bài seed");
    }

    [IntegrationFact]
    public async Task Delete_ShouldSoftDeleteInMongoAndHideFromApi()
    {
        var seed = await _factory.SeedPostAsync("Bài sẽ bị xóa");
        var (admin, _, _) = await _factory.SignInNewUserAsync("admin_dau_tien");

        var delete = await admin.DeleteAsync($"/api/posts/{seed.Id}");

        delete.StatusCode.Should().Be(HttpStatusCode.NoContent);
        (await admin.GetAsync($"/api/posts/{seed.Id}")).StatusCode.Should().Be(HttpStatusCode.NotFound);
        var raw = await _factory.RawPosts.Find(new BsonDocument("_id", ObjectId.Parse(seed.Id))).SingleAsync();
        raw["isDeleted"].AsBoolean.Should().BeTrue("xóa mềm, document vẫn còn");
        raw["deletedAt"].BsonType.Should().Be(BsonType.DateTime);
    }

    [IntegrationFact]
    public async Task GetAll_ShouldPaginateFilterByCategoryAndClampPageSize()
    {
        var sport = await _factory.SeedCategoryAsync("Thể thao");
        var news = await _factory.SeedCategoryAsync("Thời sự");
        var start = DateTime.UtcNow.AddHours(-2);
        for (var i = 0; i < 60; i++)
            await _factory.SeedPostAsync($"Bài {i:00}", categoryId: i < 15 ? sport.Id : news.Id, createdAt: start.AddMinutes(i));
        await _factory.SeedPostAsync("Bài đã xóa", categoryId: sport.Id);
        await _factory.Posts.UpdateOneAsync(p => p.Title == "Bài đã xóa", Builders<Post>.Update.Set(p => p.IsDeleted, true));
        var client = _factory.CreateClient();

        var page2 = await NewsApiFactory.ReadJsonAsync(await client.GetAsync("/api/posts?page=2&pageSize=10"));
        var sportOnly = await NewsApiFactory.ReadJsonAsync(await client.GetAsync($"/api/posts?categoryId={sport.Id}&pageSize=50"));
        var clamped = await NewsApiFactory.ReadJsonAsync(await client.GetAsync("/api/posts?pageSize=500"));

        page2.GetProperty("totalItems").GetInt64().Should().Be(60);
        page2.GetProperty("items")[0].GetProperty("title").GetString().Should().Be("Bài 49", "sắp mới nhất trước");
        sportOnly.GetProperty("totalItems").GetInt64().Should().Be(15, "bài đã xóa mềm không được tính");
        clamped.GetProperty("pageSize").GetInt32().Should().Be(50);
        clamped.GetProperty("items").GetArrayLength().Should().Be(50);
    }
}
