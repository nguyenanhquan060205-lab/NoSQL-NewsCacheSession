using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
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
        _mockRedis.Setup(r => r.IsConnected).Returns(true);
        _service = new RedisCacheService(_mockRedis.Object, NullLogger<RedisCacheService>.Instance);
    }

    [Fact]
    public async Task GetAsync_WhenRedisDisconnected_ShouldReturnNullImmediatelyWithoutCallingRedis()
    {
        _mockRedis.Setup(r => r.IsConnected).Returns(false);

        var result = await _service.GetAsync("post:1");

        result.Should().BeNull("Redis sập thì coi như MISS để đọc thẳng MongoDB");
        _mockDb.Verify(db => db.StringGetAsync(It.IsAny<RedisKey>(), It.IsAny<CommandFlags>()), Times.Never);
    }

    [Fact]
    public async Task GetAsync_WhenRedisTimesOut_ShouldReturnNull()
    {
        _mockDb.Setup(db => db.StringGetAsync("post:1", It.IsAny<CommandFlags>()))
            .ThrowsAsync(new RedisTimeoutException(CommandFlags.None, "hết thời gian chờ", CommandStatus.Sent));

        (await _service.GetAsync("post:1")).Should().BeNull();
    }

    [Fact]
    public async Task SetAndRemove_WhenRedisDisconnected_ShouldNotThrow()
    {
        _mockRedis.Setup(r => r.IsConnected).Returns(false);

        await _service.Invoking(s => s.SetAsync("post:1", "{}", TimeSpan.FromMinutes(10))).Should().NotThrowAsync();
        await _service.Invoking(s => s.RemoveAsync("post:1")).Should().NotThrowAsync();
        await _service.Invoking(s => s.ReleaseLockAsync("lock:post:1", "token")).Should().NotThrowAsync();
    }

    [Fact]
    public async Task CounterAndLock_WhenRedisDisconnected_ShouldThrowConnectionException()
    {
        _mockRedis.Setup(r => r.IsConnected).Returns(false);

        await _service.Invoking(s => s.IncrementAsync("post:1:views")).Should().ThrowAsync<RedisConnectionException>();
        await _service.Invoking(s => s.AcquireLockAsync("lock:post:1", "token", TimeSpan.FromSeconds(5)))
            .Should().ThrowAsync<RedisConnectionException>();
        await _service.Invoking(s => s.MarkDirtyViewAsync("1")).Should().ThrowAsync<RedisConnectionException>();
    }

    [Fact]
    public async Task GetAsync_WhenKeyExists_ShouldReturnValueWithoutCountingStats()
    {
        // Arrange
        _mockDb.Setup(db => db.StringGetAsync("key1", It.IsAny<CommandFlags>()))
            .ReturnsAsync((RedisValue)"cached_value");

        // Act
        var result = await _service.GetAsync("key1");

        // Assert — GetAsync còn dùng đọc bộ đếm views/posts:ver nên không được tự đếm hit/miss
        result.Should().Be("cached_value");
        _service.GetStats().TotalRequests.Should().Be(0);
    }

    [Fact]
    public async Task GetAsync_WhenKeyDoesNotExist_ShouldReturnNullWithoutCountingStats()
    {
        // Arrange
        _mockDb.Setup(db => db.StringGetAsync("missing_key", It.IsAny<CommandFlags>()))
            .ReturnsAsync(RedisValue.Null);

        // Act
        var result = await _service.GetAsync("missing_key");

        // Assert
        result.Should().BeNull();
        _service.GetStats().TotalRequests.Should().Be(0);
    }

    [Fact]
    public void RecordLookup_ShouldCountHitsAndMissesAndComputeHitRate()
    {
        // Act — 4 HIT + 1 MISS như kịch bản demo tải bài viết 5 lần
        for (var i = 0; i < 4; i++) _service.RecordLookup(hit: true);
        _service.RecordLookup(hit: false);

        // Assert
        var stats = _service.GetStats();
        stats.Hits.Should().Be(4);
        stats.Misses.Should().Be(1);
        stats.HitRate.Should().Be(80);
    }

    [Fact]
    public async Task GetAndClearDirtyViewsAsync_ShouldPopAtomicallyInsteadOfMembersThenDelete()
    {
        // Arrange
        _mockDb.Setup(db => db.SetLengthAsync("posts:dirty_views", It.IsAny<CommandFlags>()))
            .ReturnsAsync(2);
        _mockDb.Setup(db => db.SetPopAsync("posts:dirty_views", 2, It.IsAny<CommandFlags>()))
            .ReturnsAsync(new RedisValue[] { "id1", "id2" });

        // Act
        var ids = await _service.GetAndClearDirtyViewsAsync();

        // Assert
        ids.Should().BeEquivalentTo("id1", "id2");
        _mockDb.Verify(db => db.KeyDeleteAsync(It.IsAny<RedisKey>(), It.IsAny<CommandFlags>()), Times.Never);
    }

    [Fact]
    public async Task GetAndClearDirtyViewsAsync_WhenSetEmpty_ShouldNotPop()
    {
        // Arrange
        _mockDb.Setup(db => db.SetLengthAsync("posts:dirty_views", It.IsAny<CommandFlags>()))
            .ReturnsAsync(0);

        // Act
        var ids = await _service.GetAndClearDirtyViewsAsync();

        // Assert
        ids.Should().BeEmpty();
        _mockDb.Verify(db => db.SetPopAsync(It.IsAny<RedisKey>(), It.IsAny<long>(), It.IsAny<CommandFlags>()), Times.Never);
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

    [Fact]
    public async Task SetIfNotExistsAsync_ShouldUseSetNxWithoutTtl()
    {
        // Act
        await _service.SetIfNotExistsAsync("post:1:views", "500");

        // Assert — key đếm lượt xem không được có TTL và không được ghi đè số đang đếm
        // StackExchange.Redis 3.x chuyển When/TimeSpan thành điều kiện và hạn dùng dạng lệnh Redis
        // ("NX", "EX 600"...), nên so theo dạng lệnh đó.
        var call = _mockDb.Invocations.Single(i => i.Method.Name == nameof(IDatabase.StringSetAsync));
        var args = call.Arguments.Select(a => a?.ToString() ?? string.Empty).ToList();
        args.Should().Contain("post:1:views").And.Contain("500").And.Contain("NX");
        args.Should().NotContain(a => a.StartsWith("EX") || a.StartsWith("PX"));
        call.Arguments.OfType<TimeSpan>().Should().BeEmpty();
    }
}
