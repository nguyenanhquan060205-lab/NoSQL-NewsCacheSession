using Microsoft.AspNetCore.Mvc;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Posts;
using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class PostsController : ControllerBase
{
    private readonly MongoContext _mongo;
    private readonly ICacheService _cacheService;

    // Cache key prefix & TTL mặc định
    private const string CachePrefix = "post:";
    private const string ViewsPrefix = "post_views:";
    private static readonly TimeSpan CacheTtl = TimeSpan.FromMinutes(10);

    public PostsController(MongoContext mongo, ICacheService cacheService)
    {
        _mongo = mongo;
        _cacheService = cacheService;
    }

    /// <summary>
    /// Lấy danh sách bài viết (từ MongoDB, có phân trang).
    /// </summary>
    [HttpGet]
    public async Task<IActionResult> GetAll([FromQuery] int page = 1, [FromQuery] int pageSize = 10)
    {
        // TODO [SV1]: Implement lấy danh sách bài viết
        // 1. Query _mongo.Posts với Skip/Limit để phân trang
        // 2. Map sang List<PostResponse>
        // 3. Trả về 200 OK kèm danh sách

        throw new NotImplementedException();
    }

    /// <summary>
    /// Lấy chi tiết bài viết theo ID — ⭐ Cache-Aside Pattern.
    /// Bước 1: Kiểm tra Redis (cache hit?)
    /// Bước 2: Nếu miss → đọc MongoDB → ghi ngược Redis kèm TTL
    /// </summary>
    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(string id)
    {
        // TODO [SV2]: Implement Cache-Aside Pattern
        // ====== CACHE-ASIDE FLOW ======
        // Bước 1: Kiểm tra cache
        //   var cached = await _cacheService.GetAsync(CachePrefix + id);
        //   if (cached != null) → deserialize JSON → return (CACHE HIT)
        //
        // Bước 2: Cache Miss → đọc từ MongoDB
        //   var post = await _mongo.Posts.Find(p => p.Id == id).FirstOrDefaultAsync();
        //   if (post == null) → return 404
        //
        // Bước 3: Ghi ngược vào Redis kèm TTL (EXPIRE)
        //   var json = JsonSerializer.Serialize(post);
        //   await _cacheService.SetAsync(CachePrefix + id, json, CacheTtl);
        //
        // Bước 4: Trả về PostResponse
        // ==============================

        throw new NotImplementedException();
    }

    /// <summary>
    /// Tạo bài viết mới (lưu MongoDB). Yêu cầu đăng nhập.
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreatePostRequest request)
    {
        // TODO [SV1]: Implement tạo bài viết
        // 1. Lấy UserId từ HttpContext.Items["UserId"] (middleware đã set)
        // 2. Nếu chưa đăng nhập → 401
        // 3. Tạo Post mới từ request, gán AuthorId = userId
        // 4. Insert vào _mongo.Posts
        // 5. Trả về 201 Created kèm PostResponse

        throw new NotImplementedException();
    }

    /// <summary>
    /// Sửa bài viết — cập nhật MongoDB rồi ⭐ xóa Cache (Cache Invalidation).
    /// </summary>
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(string id, [FromBody] UpdatePostRequest request)
    {
        // TODO [SV2]: Implement sửa bài viết + Cache Invalidation
        // 1. Tìm post theo id trong MongoDB
        // 2. Nếu không tìm thấy → 404
        // 3. Cập nhật Title, Content, ImageUrl, UpdatedAt
        // 4. ⭐ Cache Invalidation: await _cacheService.RemoveAsync(CachePrefix + id);
        // 5. Trả về 200 OK kèm PostResponse đã cập nhật

        throw new NotImplementedException();
    }

    /// <summary>
    /// Xóa bài viết — xóa khỏi MongoDB rồi ⭐ xóa Cache (Cache Invalidation).
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(string id)
    {
        // TODO [SV1]: Implement xóa bài viết + Cache Invalidation
        // 1. Xóa post theo id trong MongoDB
        // 2. ⭐ Cache Invalidation: await _cacheService.RemoveAsync(CachePrefix + id);
        // 3. Xóa luôn view count: await _cacheService.RemoveAsync(ViewsPrefix + id);
        // 4. Trả về 204 NoContent

        throw new NotImplementedException();
    }

    /// <summary>
    /// Tăng lượt xem bài viết — ⭐ dùng INCR trên Redis (real-time counter).
    /// </summary>
    [HttpPost("{id}/view")]
    public async Task<IActionResult> IncrementView(string id)
    {
        // TODO [SV2]: Implement bộ đếm INCR lượt xem
        // 1. Gọi _cacheService.IncrementAsync(ViewsPrefix + id) → trả về lượt xem mới
        // 2. (Tuỳ chọn) Đồng bộ ngược về MongoDB mỗi N lần hoặc theo schedule
        // 3. Trả về 200 OK kèm { views: newCount }

        throw new NotImplementedException();
    }
}
