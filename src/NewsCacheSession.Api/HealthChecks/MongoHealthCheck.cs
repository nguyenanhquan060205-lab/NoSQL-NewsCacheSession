using Microsoft.Extensions.Diagnostics.HealthChecks;
using MongoDB.Bson;
using NewsCacheSession.Api.Data;

namespace NewsCacheSession.Api.HealthChecks;

public class MongoHealthCheck : IHealthCheck
{
    private readonly MongoContext _mongoContext;

    public MongoHealthCheck(MongoContext mongoContext)
    {
        _mongoContext = mongoContext;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default)
    {
        try
        {
            var command = new BsonDocument("ping", 1);
            await _mongoContext.Database.RunCommandAsync<BsonDocument>(command, cancellationToken: cancellationToken);
            return HealthCheckResult.Healthy("MongoDB connection is healthy.");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy($"MongoDB connection failed: {ex.Message}", ex);
        }
    }
}
