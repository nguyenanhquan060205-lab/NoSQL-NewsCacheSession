using Microsoft.Extensions.Diagnostics.HealthChecks;
using StackExchange.Redis;

namespace NewsCacheSession.Api.HealthChecks;

public class RedisHealthCheck : IHealthCheck
{
    private readonly IConnectionMultiplexer _redis;

    public RedisHealthCheck(IConnectionMultiplexer redis)
    {
        _redis = redis;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default)
    {
        try
        {
            var db = _redis.GetDatabase();
            var latency = await db.PingAsync();
            return HealthCheckResult.Healthy($"Redis connection is healthy. Latency: {latency.TotalMilliseconds:F2}ms");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy($"Redis connection failed: {ex.Message}", ex);
        }
    }
}
