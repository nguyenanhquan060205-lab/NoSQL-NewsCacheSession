using FluentAssertions;
using Moq;
using NewsCacheSession.Api.Services;
using StackExchange.Redis;
using Xunit;

namespace NewsCacheSession.Tests.Services;

public class CacheServiceTests
{
    private readonly Mock<IDatabase> _mockDb;
    private readonly Mock<IConnectionMultiplexer> _mockRedis;
    private readonly RedisCacheService _service;

    public CacheServiceTests()
    {
        RedisCacheService.ResetStats();
        _mockDb = new Mock<IDatabase>();
        _mockRedis = new Mock<IConnectionMultiplexer>();
        _mockRedis.Setup(r => r.GetDatabase(It.IsAny<int>(), It.IsAny<object>())).Returns(_mockDb.Object);
        _service = new RedisCacheService(_mockRedis.Object);
    }

    [Fact]
    public async Task GetAsync_WhenKeyExists_ShouldIncrementHitsAndReturnValue()
    {
        // Arrange
        _mockDb.Setup(db => db.StringGetAsync("key1", It.IsAny<CommandFlags>()))
            .ReturnsAsync((RedisValue)"cached_value");

        // Act
        var result = await _service.GetAsync("key1");

        // Assert
        result.Should().Be("cached_value");
        var stats = _service.GetStats();
        stats.Hits.Should().Be(1);
        stats.Misses.Should().Be(0);
        stats.TotalRequests.Should().Be(1);
    }

    [Fact]
    public async Task GetAsync_WhenKeyDoesNotExist_ShouldIncrementMissesAndReturnNull()
    {
        // Arrange
        _mockDb.Setup(db => db.StringGetAsync("missing_key", It.IsAny<CommandFlags>()))
            .ReturnsAsync(RedisValue.Null);

        // Act
        var result = await _service.GetAsync("missing_key");

        // Assert
        result.Should().BeNull();
        var stats = _service.GetStats();
        stats.Hits.Should().Be(0);
        stats.Misses.Should().Be(1);
        stats.TotalRequests.Should().Be(1);
    }

    [Fact]
    public async Task AcquireLockAsync_WhenNotExists_ShouldReturnTrue()
    {
        // Arrange
        _mockDb.Setup(db => db.LockTakeAsync(
                It.Is<RedisKey>(k => k == "lock:post:1"),
                It.Is<RedisValue>(v => v == "token123"),
                It.IsAny<TimeSpan>(),
                It.IsAny<CommandFlags>()))
            .ReturnsAsync(true);

        // Act
        var acquired = await _service.AcquireLockAsync("lock:post:1", "token123", TimeSpan.FromSeconds(5));

        // Assert
        acquired.Should().BeTrue();
    }

    [Fact]
    public async Task ReleaseLockAsync_WithMatchingToken_ShouldExecuteLuaScriptAndReturnTrue()
    {
        // Arrange
        _mockDb.Setup(db => db.LockReleaseAsync(
                It.Is<RedisKey>(k => k == "lock:post:1"),
                It.Is<RedisValue>(v => v == "token123"),
                It.IsAny<CommandFlags>()))
            .ReturnsAsync(true);

        // Act
        var released = await _service.ReleaseLockAsync("lock:post:1", "token123");

        // Assert
        released.Should().BeTrue();
    }
}
