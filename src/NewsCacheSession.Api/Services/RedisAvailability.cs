using StackExchange.Redis;

namespace NewsCacheSession.Api.Services;

/// <summary>
/// Nhận biết Redis đang sập để xử lý khác với lỗi lập trình.
///
/// Khi mất kết nối, StackExchange.Redis không báo lỗi ngay mà xếp lệnh vào hàng chờ (backlog)
/// tới hết <c>syncTimeout</c> (mặc định 5 giây) — đo trên stack QA: mọi request treo ~6 giây rồi
/// trả 500. Vì vậy kiểm tra <see cref="IConnectionMultiplexer.IsConnected"/> trước để báo lỗi tức thì.
/// </summary>
public static class RedisAvailability
{
    /// <summary>Lỗi do Redis không kết nối được hoặc quá thời gian chờ.</summary>
    public static bool IsOutage(Exception exception) =>
        exception is RedisConnectionException or RedisTimeoutException;

    /// <summary>Ném <see cref="RedisConnectionException"/> ngay nếu không còn kết nối nào tới Redis.</summary>
    public static void EnsureConnected(IConnectionMultiplexer redis)
    {
        if (!redis.IsConnected)
            throw new RedisConnectionException(ConnectionFailureType.UnableToConnect, CommandFlags.None,
                "Redis không kết nối được.", innerException: null, CommandStatus.WaitingToBeSent);
    }
}
