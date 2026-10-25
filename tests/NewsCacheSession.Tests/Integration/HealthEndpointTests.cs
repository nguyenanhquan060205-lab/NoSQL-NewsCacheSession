using System.Net;
using FluentAssertions;
using NewsCacheSession.Tests.Integration.Infrastructure;

namespace NewsCacheSession.Tests.Integration;

[Collection(IntegrationCollection.Name)]
public class HealthEndpointTests
{
    private readonly NewsApiFactory _factory;

    public HealthEndpointTests(NewsApiFactory factory) => _factory = factory;

    [IntegrationFact]
    public async Task Health_WithMongoAndRedisUp_ShouldReportHealthyForBoth()
    {
        var response = await _factory.CreateClient().GetAsync("/health");

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var body = await NewsApiFactory.ReadJsonAsync(response);
        body.GetProperty("status").GetString().Should().Be("Healthy");
        body.GetProperty("entries").GetProperty("mongodb").GetProperty("status").GetString().Should().Be("Healthy");
        body.GetProperty("entries").GetProperty("redis").GetProperty("status").GetString().Should().Be("Healthy");
    }
}
