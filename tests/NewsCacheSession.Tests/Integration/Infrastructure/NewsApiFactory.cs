using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using MongoDB.Bson;
using MongoDB.Driver;
using NewsCacheSession.Api.Controllers;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Api.Services;
using StackExchange.Redis;

namespace NewsCacheSession.Tests.Integration.Infrastructure;

/// <summary>
/// Dựng API thật (TestServer) trỏ vào MongoDB + Redis thật của stack QA.
///
/// An toàn dữ liệu — chặn cứng, sai là ném lỗi trước khi chạm vào DB:
///   - Mongo: database <c>newsdb_it_{guid}</c>, drop khi dispose.
///   - Redis: chỉ DB 15, FLUSHDB trước mỗi test.
/// Chuỗi kết nối lấy từ <c>NEWS_IT_MONGO</c> (mặc định <c>mongodb://localhost:27019</c>) và
/// <c>NEWS_IT_REDIS</c> (mặc định <c>localhost:6380</c>) — container QA, không phải stack demo.
///
/// <c>HealthController</c> chỉ dùng làm mốc để tìm assembly API, nhờ vậy không phải thêm
/// <c>public partial class Program</c> vào Program.cs (file dùng chung).
/// </summary>
public class NewsApiFactory : WebApplicationFactory<HealthController>
{
    public const int RedisDb = 15;
    private const string DbPrefix = "newsdb_it_";

    public static bool Enabled => Environment.GetEnvironmentVariable("NEWS_IT") == "1";

    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    private readonly string _mongoUri;
    private readonly string _redisEndpoint;
    private readonly int? _sessionTtlMinutes;
    private ConnectionMultiplexer? _redisAdmin;
    private MongoClient? _mongoClient;

    public string DatabaseName { get; } = DbPrefix + Guid.NewGuid().ToString("N")[..12];

    public NewsApiFactory() : this(null, null, null) { }

    /// <summary>
    /// Factory riêng cho một test (tự dispose). Không public vì collection fixture của xUnit
    /// chỉ cho phép đúng một constructor public.
    /// </summary>
    /// <param name="mongoUri">Đè chuỗi kết nối Mongo (ví dụ trỏ vào cổng chết để giả lập Mongo sập).</param>
    /// <param name="redisEndpoint">Đè endpoint Redis (ví dụ cổng chết để giả lập Redis sập).</param>
    /// <param name="sessionTtlMinutes">Đè <c>SessionSettings:TtlMinutes</c>.</param>
    internal NewsApiFactory(string? mongoUri, string? redisEndpoint, int? sessionTtlMinutes)
    {
        _mongoUri = mongoUri ?? Environment.GetEnvironmentVariable("NEWS_IT_MONGO") ?? "mongodb://localhost:27019";
        _redisEndpoint = redisEndpoint ?? Environment.GetEnvironmentVariable("NEWS_IT_REDIS") ?? "localhost:6380";
        _sessionTtlMinutes = sessionTtlMinutes;

        if (!DatabaseName.StartsWith(DbPrefix, StringComparison.Ordinal))
            throw new InvalidOperationException($"Tên DB test phải bắt đầu bằng {DbPrefix}.");
    }

    /// <summary>Chuỗi kết nối Redis app dùng: luôn ép <c>defaultDatabase=15</c>.</summary>
    public string AppRedisConnectionString =>
        $"{_redisEndpoint},defaultDatabase={RedisDb},abortConnect=false,connectTimeout=1000,syncTimeout=1000";

    protected override IHost CreateHost(IHostBuilder builder)
    {
        // Program.cs đọc chuỗi kết nối Redis TRƯỚC builder.Build(), nên đè qua
        // ConfigureAppConfiguration không kịp. Biến môi trường thì chắc chắn được đọc.
        // Đặt ngay trước khi Program chạy (không đặt trong constructor) để nhiều factory
        // tạo nối tiếp nhau không ghi đè cấu hình của nhau.
        var options = ConfigurationOptions.Parse(AppRedisConnectionString);
        if (options.DefaultDatabase != RedisDb)
            throw new InvalidOperationException("Integration test chỉ được dùng Redis DB 15.");

        Environment.SetEnvironmentVariable("MongoSettings__ConnectionString", _mongoUri);
        Environment.SetEnvironmentVariable("MongoSettings__DatabaseName", DatabaseName);
        Environment.SetEnvironmentVariable("RedisSettings__ConnectionString", AppRedisConnectionString);
        Environment.SetEnvironmentVariable("SessionSettings__TtlMinutes", _sessionTtlMinutes?.ToString());
        builder.UseEnvironment("Development");
        return base.CreateHost(builder);
    }

    // ===== Truy cập thẳng Redis / Mongo để kiểm tra trạng thái =====

    public IDatabase Redis => RedisAdmin.GetDatabase(RedisDb);

    private ConnectionMultiplexer RedisAdmin => _redisAdmin ??=
        ConnectionMultiplexer.Connect($"{Environment.GetEnvironmentVariable("NEWS_IT_REDIS") ?? "localhost:6380"},allowAdmin=true");

    public IMongoDatabase Mongo => (_mongoClient ??= new MongoClient(
        Environment.GetEnvironmentVariable("NEWS_IT_MONGO") ?? "mongodb://localhost:27019")).GetDatabase(DatabaseName);

    public IMongoCollection<Post> Posts => Mongo.GetCollection<Post>("posts");
    public IMongoCollection<BsonDocument> RawPosts => Mongo.GetCollection<BsonDocument>("posts");
    public IMongoCollection<User> Users => Mongo.GetCollection<User>("users");
    public IMongoCollection<Category> Categories => Mongo.GetCollection<Category>("categories");

    public List<string> RedisKeys(string pattern) =>
        RedisAdmin.GetServers().First().Keys(RedisDb, pattern).Select(k => k.ToString()).ToList();

    /// <summary>
    /// Về trạng thái sạch trước mỗi test: FLUSHDB Redis 15, xóa document (giữ index do
    /// MongoIndexInitializer tạo lúc khởi động), xóa thống kê hit/miss.
    /// </summary>
    public async Task ResetAsync()
    {
        _ = Server; // khởi động host trước để index đã được tạo
        foreach (var server in RedisAdmin.GetServers())
            await server.FlushDatabaseAsync(RedisDb);

        await Posts.DeleteManyAsync(FilterDefinition<Post>.Empty);
        await Users.DeleteManyAsync(FilterDefinition<User>.Empty);
        await Categories.DeleteManyAsync(FilterDefinition<Category>.Empty);
        await Mongo.GetCollection<BsonDocument>("meta").DeleteManyAsync(FilterDefinition<BsonDocument>.Empty);
        RedisCacheService.ResetStats();
    }

    public ViewCountSyncWorker ViewWorker =>
        Services.GetServices<IHostedService>().OfType<ViewCountSyncWorker>().Single();

    // ===== Dữ liệu mẫu =====

    public async Task<Category> SeedCategoryAsync(string name)
    {
        var category = new Category { Id = ObjectId.GenerateNewId().ToString(), Name = name, Slug = name.ToLowerInvariant() };
        await Categories.InsertOneAsync(category);
        return category;
    }

    public async Task<Post> SeedPostAsync(string title, int views = 0, string? categoryId = null,
        string? authorId = null, DateTime? createdAt = null, string? imagePublicId = null)
    {
        var at = createdAt ?? DateTime.UtcNow;
        var post = new Post
        {
            Id = ObjectId.GenerateNewId().ToString(),
            Title = title,
            Slug = $"seed-{Guid.NewGuid():N}",
            Content = $"Nội dung {title}",
            ImageUrl = "https://picsum.photos/seed/it/800/450",
            ImagePublicId = imagePublicId,
            CategoryId = categoryId,
            AuthorId = authorId,
            Views = views,
            CreatedAt = at,
            UpdatedAt = at
        };
        await Posts.InsertOneAsync(post);
        return post;
    }

    // ===== Tài khoản =====

    public static string NewPassword() => "Pw-" + Guid.NewGuid().ToString("N")[..16];

    public static Task<HttpResponseMessage> RegisterAsync(HttpClient client, string username, string password) =>
        client.PostAsJsonAsync("/api/auth/register", new { username, password });

    /// <summary>Đăng nhập bằng client (cookie được client giữ lại), trả về sessionId.</summary>
    public static async Task<string> LoginAsync(HttpClient client, string username, string password)
    {
        var response = await client.PostAsJsonAsync("/api/auth/login", new { username, password });
        if (response.StatusCode != HttpStatusCode.OK)
            throw new InvalidOperationException($"Đăng nhập {username} thất bại: {(int)response.StatusCode}");
        var body = await response.Content.ReadFromJsonAsync<JsonElement>(Json);
        return body.GetProperty("sessionId").GetString()!;
    }

    /// <summary>Đăng ký rồi đăng nhập trên một client mới; trả về client đã có cookie phiên.</summary>
    public async Task<(HttpClient Client, string SessionId, string UserId)> SignInNewUserAsync(string username)
    {
        var client = CreateClient();
        var password = NewPassword();
        var register = await RegisterAsync(client, username, password);
        if (register.StatusCode != HttpStatusCode.Created)
            throw new InvalidOperationException($"Đăng ký {username} thất bại: {(int)register.StatusCode}");
        var userId = (await register.Content.ReadFromJsonAsync<JsonElement>(Json)).GetProperty("id").GetString()!;
        var sessionId = await LoginAsync(client, username, password);
        return (client, sessionId, userId);
    }

    public static async Task<JsonElement> ReadJsonAsync(HttpResponseMessage response) =>
        await response.Content.ReadFromJsonAsync<JsonElement>(Json);

    public static string? CacheHeader(HttpResponseMessage response) =>
        response.Headers.TryGetValues("X-Cache", out var values) ? values.FirstOrDefault() : null;

    public override async ValueTask DisposeAsync()
    {
        try
        {
            if (_mongoClient != null || Enabled)
                await Mongo.Client.DropDatabaseAsync(DatabaseName);
        }
        catch
        {
            // Mongo test có thể đã bị trỏ vào cổng chết — không có gì để dọn.
        }

        _redisAdmin?.Dispose();
        await base.DisposeAsync();
    }
}
