using MongoDB.Driver;
using NewsCacheSession.Api.Models;

namespace NewsCacheSession.Api.Data;

/// <summary>
/// Tạo index cho MongoDB lúc ứng dụng khởi động (xem bảng index trong docs/mongodb-schema.md).
/// Chạy một lần khi start; CreateMany là idempotent nên gọi lại nhiều lần vô hại.
///
/// Đăng ký trong Program.cs:
///     builder.Services.AddHostedService&lt;MongoIndexInitializer&gt;();
/// </summary>
public class MongoIndexInitializer : IHostedService
{
    private readonly MongoContext _mongo;
    private readonly ILogger<MongoIndexInitializer> _logger;

    public MongoIndexInitializer(MongoContext mongo, ILogger<MongoIndexInitializer> logger)
    {
        _mongo = mongo;
        _logger = logger;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        try
        {
            // posts.slug unique — tra cứu bài viết theo URL, đồng thời chặn trùng slug ở tầng DB
            // (GenerateUniqueSlugAsync chỉ chống trùng bằng query nên vẫn có race condition).
            await _mongo.Posts.Indexes.CreateManyAsync(new[]
            {
                new CreateIndexModel<Post>(
                    Builders<Post>.IndexKeys.Ascending(p => p.Slug),
                    new CreateIndexOptions { Unique = true, Name = "ux_posts_slug" }),

                // Lọc danh sách theo chuyên mục + sắp theo ngày tạo (SCRUM-18)
                new CreateIndexModel<Post>(
                    Builders<Post>.IndexKeys
                        .Ascending(p => p.CategoryId)
                        .Descending(p => p.CreatedAt),
                    new CreateIndexOptions { Name = "ix_posts_category_createdAt" }),

                // Trang chủ: sắp bài mới nhất trước
                new CreateIndexModel<Post>(
                    Builders<Post>.IndexKeys.Descending(p => p.CreatedAt),
                    new CreateIndexOptions { Name = "ix_posts_createdAt" })
            }, cancellationToken);

            // users.username unique — chặn trùng tài khoản ở tầng DB, không chỉ dựa vào
            // kiểm tra trong AuthController.Register.
            await _mongo.Users.Indexes.CreateOneAsync(
                new CreateIndexModel<User>(
                    Builders<User>.IndexKeys.Ascending(u => u.Username),
                    new CreateIndexOptions { Unique = true, Name = "ux_users_username" }),
                cancellationToken: cancellationToken);

            // categories.slug unique
            await _mongo.Database.GetCollection<Category>("categories").Indexes.CreateOneAsync(
                new CreateIndexModel<Category>(
                    Builders<Category>.IndexKeys.Ascending(c => c.Slug),
                    new CreateIndexOptions { Unique = true, Name = "ux_categories_slug" }),
                cancellationToken: cancellationToken);

            _logger.LogInformation("Đã tạo index MongoDB cho posts, users, categories.");
        }
        catch (Exception ex)
        {
            // Không chặn ứng dụng khởi động nếu MongoDB chưa sẵn sàng — /health sẽ báo.
            _logger.LogWarning(ex, "Không tạo được index MongoDB.");
        }
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
