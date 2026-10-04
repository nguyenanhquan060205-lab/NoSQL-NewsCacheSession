using FluentAssertions;
using Moq;
using NewsCacheSession.Api.Services;
using StackExchange.Redis;
using Xunit;

namespace NewsCacheSession.Tests.Services;

public class SessionServiceTests
{
    private readonly Mock<IDatabase> _mockDb;
    private readonly Mock<IConnectionMultiplexer> _mockRedis;
    private readonly RedisSessionService _service;

    public SessionServiceTests()
    {
        _mockDb = new Mock<IDatabase>();
        _mockRedis = new Mock<IConnectionMultiplexer>();
        _mockRedis.Setup(r => r.GetDatabase(It.IsAny<int>(), It.IsAny<object>())).Returns(_mockDb.Object);
        _service = new RedisSessionService(_mockRedis.Object);
    }

    [Fact]
    public async Task CreateSessionAsync_WithRole_ShouldStoreAllRequiredHashEntriesAndSetTtl()
    {
        // Arrange
        var sessionId = "sess-123";
        var userId = "user-456";
        var username = "testuser";
        var role = "admin";
        var ttl = TimeSpan.FromMinutes(30);

        HashEntry[]? savedEntries = null;
        _mockDb.Setup(db => db.HashSetAsync(
                It.Is<RedisKey>(k => k == $"session:{sessionId}"),
                It.IsAny<HashEntry[]>(),
                It.IsAny<CommandFlags>()))
            .Callback<RedisKey, HashEntry[], CommandFlags>((k, entries, f) => savedEntries = entries)
            .Returns(Task.CompletedTask);

        _mockDb.Setup(db => db.KeyExpireAsync(
                It.Is<RedisKey>(k => k == $"session:{sessionId}"),
                It.Is<TimeSpan?>(t => t == ttl),
                It.IsAny<ExpireWhen>(),
                It.IsAny<CommandFlags>()))
            .ReturnsAsync(true);

        // Act
        await _service.CreateSessionAsync(sessionId, userId, username, role, ttl);

        // Assert
        savedEntries.Should().NotBeNull();
        var dict = savedEntries!.ToDictionary(e => e.Name.ToString(), e => e.Value.ToString());

        dict.Should().ContainKey("userId").WhoseValue.Should().Be(userId);
        dict.Should().ContainKey("username").WhoseValue.Should().Be(username);
        dict.Should().ContainKey("role").WhoseValue.Should().Be(role);
        dict.Should().ContainKey("loginAt").WhoseValue.Should().NotBeNullOrEmpty();
        dict.Should().ContainKey("lastActive").WhoseValue.Should().NotBeNullOrEmpty();

        _mockDb.Verify(db => db.KeyExpireAsync($"session:{sessionId}", ttl, It.IsAny<ExpireWhen>(), It.IsAny<CommandFlags>()), Times.Once);
    }

    [Fact]
    public async Task GetSessionAsync_WhenExists_ShouldReturnDictionary()
    {
        // Arrange
        var sessionId = "sess-123";
        var entries = new HashEntry[]
        {
            new("userId", "user-1"),
            new("username", "user1"),
            new("role", "user"),
            new("loginAt", "1700000000"),
            new("lastActive", "1700000000")
        };

        _mockDb.Setup(db => db.HashGetAllAsync($"session:{sessionId}", It.IsAny<CommandFlags>()))
            .ReturnsAsync(entries);

        // Act
        var result = await _service.GetSessionAsync(sessionId);

        // Assert
        result.Should().NotBeNull();
        result!["userId"].Should().Be("user-1");
        result["role"].Should().Be("user");
    }

    [Fact]
    public async Task RefreshSessionAsync_ShouldCallKeyExpire()
    {
        // Arrange
        var sessionId = "sess-123";
        var ttl = TimeSpan.FromMinutes(30);

        _mockDb.Setup(db => db.KeyExpireAsync(
                $"session:{sessionId}",
                It.Is<TimeSpan?>(t => t == ttl),
                It.IsAny<ExpireWhen>(),
                It.IsAny<CommandFlags>()))
            .ReturnsAsync(true);

        // Act
        await _service.RefreshSessionAsync(sessionId, ttl);

        // Assert
        _mockDb.Verify(db => db.KeyExpireAsync($"session:{sessionId}", ttl, It.IsAny<ExpireWhen>(), It.IsAny<CommandFlags>()), Times.Once);
    }

    [Fact]
    public async Task RemoveSessionAsync_ShouldDeleteKey()
    {
        // Arrange
        var sessionId = "sess-123";

        _mockDb.Setup(db => db.KeyDeleteAsync($"session:{sessionId}", It.IsAny<CommandFlags>()))
            .ReturnsAsync(true);

        // Act
        await _service.RemoveSessionAsync(sessionId);

        // Assert
        _mockDb.Verify(db => db.KeyDeleteAsync($"session:{sessionId}", It.IsAny<CommandFlags>()), Times.Once);
    }
}
