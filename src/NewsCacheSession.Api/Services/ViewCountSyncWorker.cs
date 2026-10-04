using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.Models;

namespace NewsCacheSession.Api.Services;

/// <summary>
/// Background Service định kỳ flush bộ đếm lượt xem từ Redis về MongoDB (SCRUM-25).
/// Áp dụng kỹ thuật Write-Behind Pattern để giảm tải ghi cho MongoDB.
/// </summary>
public class ViewCountSyncWorker : BackgroundService
{
    private readonly IServiceProvider _services;
    private readonly ILogger<ViewCountSyncWorker> _logger;
    private readonly TimeSpan _period = TimeSpan.FromMinutes(1);

    public ViewCountSyncWorker(IServiceProvider services, ILogger<ViewCountSyncWorker> logger)
    {
        _services = services;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("ViewCountSyncWorker đã khởi động.");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(_period, stoppingToken);
                await FlushViewsToMongoAsync(stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Lỗi xảy ra trong ViewCountSyncWorker khi đồng bộ views.");
            }
        }

        _logger.LogInformation("ViewCountSyncWorker đã dừng.");
    }

    public async Task FlushViewsToMongoAsync(CancellationToken ct)
    {
        using var scope = _services.CreateScope();
        var cache = scope.ServiceProvider.GetRequiredService<ICacheService>();
        var mongo = scope.ServiceProvider.GetRequiredService<MongoContext>();

        var dirtyPostIds = await cache.GetAndClearDirtyViewsAsync();
        if (dirtyPostIds.Count == 0) return;

        _logger.LogInformation("Đồng bộ lượt xem cho {Count} bài viết về MongoDB.", dirtyPostIds.Count);

        foreach (var postId in dirtyPostIds)
        {
            var viewsStr = await cache.GetAsync($"post:{postId}:views");
            if (int.TryParse(viewsStr, out var views))
            {
                await mongo.Posts.UpdateOneAsync(
                    p => p.Id == postId,
                    Builders<Post>.Update.Set(p => p.Views, views),
                    cancellationToken: ct);
            }
        }
    }
}
