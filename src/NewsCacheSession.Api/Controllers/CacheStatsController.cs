using Microsoft.AspNetCore.Mvc;
using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Controllers;

[ApiController]
[Route("api/cache")]
public class CacheStatsController : ControllerBase
{
    private readonly ICacheService _cacheService;

    public CacheStatsController(ICacheService cacheService)
    {
        _cacheService = cacheService;
    }

    /// <summary>
    /// Thống kê tỷ lệ Hit/Miss của Redis Cache (SCRUM-34).
    /// Dùng cho việc chấm điểm hiệu năng và hiển thị tỷ lệ trên trang kiểm thử.
    /// </summary>
    [HttpGet("stats")]
    public IActionResult GetStats()
    {
        var stats = _cacheService.GetStats();
        return Ok(stats);
    }
}
