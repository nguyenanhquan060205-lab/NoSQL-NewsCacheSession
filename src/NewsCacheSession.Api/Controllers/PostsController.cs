using Microsoft.AspNetCore.Mvc;
using MongoDB.Bson;
using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Posts;
using NewsCacheSession.Api.Models;
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

    private const int MaxPageSize = 50;

    // Bài viết chưa bị xóa mềm. Dùng Ne(true) để khớp cả document cũ chưa có field IsDeleted.
    private static readonly FilterDefinition<Post> NotDeleted =
        Builders<Post>.Filter.Ne(p => p.IsDeleted, true);

    public PostsController(MongoContext mongo, ICacheService cacheService)
    {
        _mongo = mongo;
        _cacheService = cacheService;
    }

    /// <summary>
    /// Lấy danh sách bài viết (từ MongoDB, có phân trang + lọc theo chuyên mục).
    /// </summary>
    [HttpGet]
    public async Task<IActionResult> GetAll(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 10,
        [FromQuery] string? categoryId = null)
    {
        page = Math.Max(page, 1);
        pageSize = Math.Clamp(pageSize, 1, MaxPageSize);

        var filter = NotDeleted;
        if (!string.IsNullOrWhiteSpace(categoryId))
        {
            if (!ObjectId.TryParse(categoryId, out _))
                return BadRequest(new { message = "ID chuyên mục không hợp lệ." });

            filter &= Builders<Post>.Filter.Eq(p => p.CategoryId, categoryId);
        }

        var totalItems = await _mongo.Posts.CountDocumentsAsync(filter);
        var posts = await _mongo.Posts.Find(filter)
            .SortByDescending(p => p.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Limit(pageSize)
            .ToListAsync();

        return Ok(new PagedPostsResponse
        {
            Items = posts.Select(PostResponse.FromModel).ToList(),
            Page = page,
            PageSize = pageSize,
            TotalItems = totalItems,
            TotalPages = (int)Math.Ceiling(totalItems / (double)pageSize)
        });
    }

    /// <summary>
    /// Lấy chi tiết bài viết theo slug (đọc thẳng MongoDB, chưa cache).
    /// </summary>
    [HttpGet("slug/{slug}")]
    public async Task<IActionResult> GetBySlug(string slug)
    {
        var filter = NotDeleted & Builders<Post>.Filter.Eq(p => p.Slug, slug.ToLowerInvariant());
        var post = await _mongo.Posts.Find(filter).FirstOrDefaultAsync();
        if (post == null)
            return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });

        return Ok(PostResponse.FromModel(post));
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
    /// Xóa mềm bài viết trong MongoDB rồi ⭐ xóa Cache (Cache Invalidation).
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(string id)
    {
        if (!ObjectId.TryParse(id, out var objectId))
        {
            return BadRequest(new { message = "ID bài viết không hợp lệ." });
        }

        // Ghép filter BSON tường minh để vừa khớp _id kiểu ObjectId, vừa hỗ trợ
        // các document cũ chưa có field IsDeleted.
        var filter = Builders<Post>.Filter.And(
            new BsonDocument("_id", objectId),
            new BsonDocument("$or", new BsonArray
            {
                new BsonDocument("IsDeleted", false),
                new BsonDocument("IsDeleted", new BsonDocument("$exists", false))
            }));

        var now = DateTime.UtcNow;
        var update = Builders<Post>.Update
            .Set(post => post.IsDeleted, true)
            .Set(post => post.DeletedAt, now)
            .Set(post => post.UpdatedAt, now);

        var result = await _mongo.Posts.UpdateOneAsync(filter, update);
        if (result.MatchedCount == 0)
        {
            return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });
        }

        // Cache-Aside: sau khi DB gốc thay đổi, xóa ngay dữ liệu Redis liên quan
        // để request tiếp theo không đọc lại nội dung hoặc bộ đếm đã cũ.
        await Task.WhenAll(
            _cacheService.RemoveAsync(CachePrefix + id),
            _cacheService.RemoveAsync(ViewsPrefix + id));

        return NoContent();
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
