using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
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
    private readonly ISessionService _sessionService;

    // Cache key prefix & TTL mặc định
    private const string CachePrefix = "post:";
    private const string ViewsPrefix = "post_views:";
    private static readonly TimeSpan CacheTtl = TimeSpan.FromMinutes(10);

    private const int MaxPageSize = 50;

    // Bài viết chưa bị xóa mềm. Dùng Ne(true) để khớp cả document cũ chưa có field IsDeleted.
    private static readonly FilterDefinition<Post> NotDeleted =
        Builders<Post>.Filter.Ne(p => p.IsDeleted, true);

    public PostsController(MongoContext mongo, ICacheService cacheService, ISessionService sessionService)
    {
        _mongo = mongo;
        _cacheService = cacheService;
        _sessionService = sessionService;
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
        var userId = await GetCurrentUserIdAsync();
        if (userId == null)
            return Unauthorized(new { message = "Bạn cần đăng nhập để tạo bài viết." });

        if (!IsValidCategoryId(request.CategoryId))
            return BadRequest(new { message = "ID chuyên mục không hợp lệ." });

        var now = DateTime.UtcNow;
        var post = new Post
        {
            Title = request.Title.Trim(),
            Slug = await GenerateUniqueSlugAsync(request.Title),
            Content = request.Content,
            ImageUrl = request.ImageUrl,
            CategoryId = NullIfEmpty(request.CategoryId),
            AuthorId = userId,
            CreatedAt = now,
            UpdatedAt = now
        };
        await _mongo.Posts.InsertOneAsync(post);

        return CreatedAtAction(nameof(GetBySlug), new { slug = post.Slug }, PostResponse.FromModel(post));
    }

    /// <summary>
    /// Sửa bài viết — cập nhật MongoDB rồi ⭐ xóa Cache (Cache Invalidation).
    /// Slug giữ nguyên khi đổi tiêu đề để link cũ không bị hỏng.
    /// </summary>
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(string id, [FromBody] UpdatePostRequest request)
    {
        var userId = await GetCurrentUserIdAsync();
        if (userId == null)
            return Unauthorized(new { message = "Bạn cần đăng nhập để sửa bài viết." });

        if (!ObjectId.TryParse(id, out _))
            return BadRequest(new { message = "ID bài viết không hợp lệ." });

        if (!IsValidCategoryId(request.CategoryId))
            return BadRequest(new { message = "ID chuyên mục không hợp lệ." });

        var filter = NotDeleted & Builders<Post>.Filter.Eq(p => p.Id, id);
        var post = await _mongo.Posts.Find(filter).FirstOrDefaultAsync();
        if (post == null)
            return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });

        if (!CanModify(post, userId))
            return StatusCode(StatusCodes.Status403Forbidden, new { message = "Bạn không có quyền sửa bài viết này." });

        var update = Builders<Post>.Update
            .Set(p => p.Title, request.Title.Trim())
            .Set(p => p.Content, request.Content)
            .Set(p => p.ImageUrl, request.ImageUrl)
            .Set(p => p.CategoryId, NullIfEmpty(request.CategoryId))
            .Set(p => p.UpdatedAt, DateTime.UtcNow);

        var updated = await _mongo.Posts.FindOneAndUpdateAsync(filter, update,
            new FindOneAndUpdateOptions<Post> { ReturnDocument = ReturnDocument.After });
        if (updated == null)
            return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });

        // Cache Invalidation: DB gốc đã đổi → xóa bản cache cũ
        await _cacheService.RemoveAsync(CachePrefix + id);

        return Ok(PostResponse.FromModel(updated));
    }

    /// <summary>
    /// Xóa mềm bài viết trong MongoDB rồi ⭐ xóa Cache (Cache Invalidation).
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(string id)
    {
        var userId = await GetCurrentUserIdAsync();
        if (userId == null)
            return Unauthorized(new { message = "Bạn cần đăng nhập để xóa bài viết." });

        if (!ObjectId.TryParse(id, out _))
        {
            return BadRequest(new { message = "ID bài viết không hợp lệ." });
        }

        var filter = NotDeleted & Builders<Post>.Filter.Eq(p => p.Id, id);
        var post = await _mongo.Posts.Find(filter).FirstOrDefaultAsync();
        if (post == null)
        {
            return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });
        }

        if (!CanModify(post, userId))
        {
            return StatusCode(StatusCodes.Status403Forbidden, new { message = "Bạn không có quyền xóa bài viết này." });
        }

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

    // ===== Helpers =====

    /// <summary>
    /// Lấy UserId của người đang đăng nhập: ưu tiên giá trị SessionAuthMiddleware đã gán,
    /// nếu chưa có thì tự đọc session trên Redis từ Cookie "SessionId" / Header "X-Session-Id".
    /// </summary>
    private async Task<string?> GetCurrentUserIdAsync()
    {
        if (HttpContext.Items["UserId"] is string userId && !string.IsNullOrEmpty(userId))
            return userId;

        var sessionId = Request.Cookies["SessionId"] ?? Request.Headers["X-Session-Id"].FirstOrDefault();
        if (string.IsNullOrEmpty(sessionId))
            return null;

        var session = await _sessionService.GetSessionAsync(sessionId);
        return session?.GetValueOrDefault("userId");
    }

    // Bài không có tác giả (vd. dữ liệu seed) thì ai đăng nhập cũng sửa/xóa được
    private static bool CanModify(Post post, string userId) =>
        string.IsNullOrEmpty(post.AuthorId) || post.AuthorId == userId;

    private static bool IsValidCategoryId(string? categoryId) =>
        string.IsNullOrWhiteSpace(categoryId) || ObjectId.TryParse(categoryId, out _);

    private static string? NullIfEmpty(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    /// <summary>
    /// "Tin nóng hôm nay!" → "tin-nong-hom-nay" (bỏ dấu tiếng Việt, chỉ giữ a-z, 0-9, '-').
    /// </summary>
    private static string ToSlug(string text)
    {
        var normalized = text.Trim().ToLowerInvariant()
            .Replace('đ', 'd')
            .Normalize(NormalizationForm.FormD);

        var sb = new StringBuilder();
        foreach (var c in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }

        var slug = Regex.Replace(sb.ToString(), "[^a-z0-9]+", "-").Trim('-');
        return string.IsNullOrEmpty(slug) ? "bai-viet" : slug;
    }

    /// <summary>
    /// Sinh slug không trùng: nếu đã có thì thêm hậu tố -2, -3, ...
    /// Kiểm tra cả bài đã xóa mềm để slug cũ không bị dùng lại.
    /// </summary>
    private async Task<string> GenerateUniqueSlugAsync(string title)
    {
        var baseSlug = ToSlug(title);
        var slug = baseSlug;
        for (var i = 2; await _mongo.Posts.Find(p => p.Slug == slug).AnyAsync(); i++)
            slug = $"{baseSlug}-{i}";

        return slug;
    }
}
