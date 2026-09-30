using Microsoft.AspNetCore.Mvc;
using MongoDB.Bson;
using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Posts;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Api.Services;
using NewsCacheSession.Api.Utils;

namespace NewsCacheSession.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class PostsController : ControllerBase
{
    private readonly MongoContext _mongo;
    private readonly ICacheService _cacheService;
    private readonly ICurrentUserService _currentUser;

    // ===== Hợp đồng keyspace Redis — xem docs/redis-keyspace.md =====
    // Mọi key liên quan bài viết nằm chung namespace "post:" / "posts:" để SCAN gom được hết.
    private const string CachePrefix = "post:";              // post:{id}         — String JSON, TTL 10 phút
    private const string ListCachePrefix = "posts:cat:";     // posts:cat:{catId}:p{n}:v{ver} — SV2 (SCRUM-26)
    private const string ListVersionKey = "posts:ver";       // bộ đếm phiên bản cache danh sách
    private static readonly TimeSpan CacheTtl = TimeSpan.FromMinutes(10);

    /// <summary>Key cache nội dung bài viết: <c>post:{id}</c>.</summary>
    private static string CacheKey(string id) => CachePrefix + id;

    /// <summary>Key bộ đếm lượt xem (INCR, không TTL): <c>post:{id}:views</c>.</summary>
    private static string ViewsKey(string id) => $"{CachePrefix}{id}:views";

    /// <summary>
    /// Vô hiệu hóa TOÀN BỘ cache danh sách bằng cách tăng số phiên bản (cache key versioning).
    ///
    /// Cách thường thấy là SCAN tìm rồi DEL từng key <c>posts:cat:*</c>, nhưng SCAN là O(N) theo
    /// số key và phải lặp nhiều lượt. Ở đây chỉ cần một lệnh INCR: key cũ mang số phiên bản
    /// nhỏ hơn nên không ai tra tới nữa, và tự biến mất khi hết TTL 3 phút.
    ///
    /// SV2 (SCRUM-26) khi dựng key cache danh sách phải đọc số này và ghép vào key:
    /// <c>posts:cat:{categoryId}:p{page}:v{ver}</c>.
    /// </summary>
    private Task BumpListVersionAsync() => _cacheService.IncrementAsync(ListVersionKey);

    private const int MaxPageSize = 50;

    // Bài viết chưa bị xóa mềm. Dùng Ne(true) để khớp cả document cũ chưa có field IsDeleted.
    private static readonly FilterDefinition<Post> NotDeleted =
        Builders<Post>.Filter.Ne(p => p.IsDeleted, true);

    public PostsController(MongoContext mongo, ICacheService cacheService, ICurrentUserService currentUser)
    {
        _mongo = mongo;
        _cacheService = cacheService;
        _currentUser = currentUser;
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
        //   var cached = await _cacheService.GetAsync(CacheKey(id));
        //   if (cached != null) → deserialize JSON → return (CACHE HIT)
        //
        // Bước 2: Cache Miss → đọc từ MongoDB
        //   var post = await _mongo.Posts.Find(p => p.Id == id).FirstOrDefaultAsync();
        //   if (post == null) → return 404
        //
        // Bước 3: Ghi ngược vào Redis kèm TTL (EXPIRE)
        //   var json = JsonSerializer.Serialize(post);
        //   await _cacheService.SetAsync(CacheKey(id), json, CacheTtl);
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
        var current = await _currentUser.GetAsync(HttpContext);
        if (current == null)
            return Unauthorized(new { message = "Bạn cần đăng nhập để tạo bài viết." });

        if (!await IsValidCategoryAsync(request.CategoryId))
            return BadRequest(new { message = "Chuyên mục không hợp lệ hoặc không tồn tại." });

        var now = DateTime.UtcNow;
        var post = new Post
        {
            Title = request.Title.Trim(),
            Slug = await GenerateUniqueSlugAsync(request.Title),
            Content = request.Content,
            ImageUrl = request.ImageUrl,
            CategoryId = NullIfEmpty(request.CategoryId),
            AuthorId = current.UserId,
            CreatedAt = now,
            UpdatedAt = now
        };
        await _mongo.Posts.InsertOneAsync(post);

        // Bài mới phải xuất hiện trên trang chủ ngay, không đợi hết TTL cache danh sách.
        await BumpListVersionAsync();

        return CreatedAtAction(nameof(GetBySlug), new { slug = post.Slug }, PostResponse.FromModel(post));
    }

    /// <summary>
    /// Sửa bài viết — cập nhật MongoDB rồi ⭐ xóa Cache (Cache Invalidation).
    /// Slug giữ nguyên khi đổi tiêu đề để link cũ không bị hỏng.
    /// </summary>
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(string id, [FromBody] UpdatePostRequest request)
    {
        var current = await _currentUser.GetAsync(HttpContext);
        if (current == null)
            return Unauthorized(new { message = "Bạn cần đăng nhập để sửa bài viết." });

        if (!ObjectId.TryParse(id, out _))
            return BadRequest(new { message = "ID bài viết không hợp lệ." });

        if (!await IsValidCategoryAsync(request.CategoryId))
            return BadRequest(new { message = "Chuyên mục không hợp lệ hoặc không tồn tại." });

        var filter = NotDeleted & Builders<Post>.Filter.Eq(p => p.Id, id);
        var post = await _mongo.Posts.Find(filter).FirstOrDefaultAsync();
        if (post == null)
            return NotFound(new { message = "Bài viết không tồn tại hoặc đã bị xóa." });

        if (!CanModify(post, current))
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

        // Cache Invalidation — DB gốc đã đổi nên phải bỏ bản cache cũ:
        //   1. xóa cache nội dung bài viết
        //   2. tăng phiên bản để cache danh sách (tiêu đề/chuyên mục có thể đã đổi) hết hiệu lực
        await Task.WhenAll(
            _cacheService.RemoveAsync(CacheKey(id)),
            BumpListVersionAsync());

        return Ok(PostResponse.FromModel(updated));
    }

    /// <summary>
    /// Xóa mềm bài viết trong MongoDB rồi ⭐ xóa Cache (Cache Invalidation).
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(string id)
    {
        var current = await _currentUser.GetAsync(HttpContext);
        if (current == null)
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

        if (!CanModify(post, current))
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

        // Cache Invalidation: xóa bản cache nội dung + hạ hiệu lực cache danh sách.
        // KHÔNG xóa post:{id}:views — đây là xóa mềm (bài có thể phục hồi) và lượt xem
        // là số liệu tích lũy, phải để job flush của SV2 chốt về MongoDB trước.
        await Task.WhenAll(
            _cacheService.RemoveAsync(CacheKey(id)),
            BumpListVersionAsync());

        return NoContent();
    }

    /// <summary>
    /// Tăng lượt xem bài viết — ⭐ dùng INCR trên Redis (real-time counter).
    /// </summary>
    [HttpPost("{id}/view")]
    public async Task<IActionResult> IncrementView(string id)
    {
        // TODO [SV2]: Implement bộ đếm INCR lượt xem
        // 1. Gọi _cacheService.IncrementAsync(ViewsKey(id)) → trả về lượt xem mới
        // 2. (Tuỳ chọn) Đồng bộ ngược về MongoDB mỗi N lần hoặc theo schedule
        // 3. Trả về 200 OK kèm { views: newCount }

        throw new NotImplementedException();
    }

    // ===== Helpers =====

    /// <summary>
    /// Quy tắc sửa/xóa bài viết:
    /// <list type="bullet">
    ///   <item>admin — sửa/xóa được mọi bài, kể cả bài không có tác giả (100 bài seed)</item>
    ///   <item>người dùng thường — chỉ sửa/xóa bài mình viết</item>
    /// </list>
    /// Bài không có authorId thuộc trách nhiệm quản trị, nên không để ai đăng nhập cũng sửa
    /// được như trước — nếu không thì mọi tài khoản đều xóa được 100 bài seed.
    /// </summary>
    private static bool CanModify(Post post, CurrentUser current) =>
        current.IsAdmin || (!string.IsNullOrEmpty(post.AuthorId) && post.AuthorId == current.UserId);

    // Collection "categories" lấy qua MongoContext.Database để không phải sửa MongoContext.cs (file dùng chung).
    private IMongoCollection<Category> Categories => _mongo.Database.GetCollection<Category>("categories");

    /// <summary>
    /// Chuyên mục hợp lệ = để trống, hoặc là ObjectId thật sự tồn tại trong collection "categories".
    /// Kiểm tra tồn tại để tránh bài viết trỏ vào chuyên mục đã bị xóa (orphan reference).
    /// </summary>
    private async Task<bool> IsValidCategoryAsync(string? categoryId)
    {
        if (string.IsNullOrWhiteSpace(categoryId))
            return true;

        if (!ObjectId.TryParse(categoryId, out _))
            return false;

        return await Categories.Find(c => c.Id == categoryId).AnyAsync();
    }

    private static string? NullIfEmpty(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    /// <summary>
    /// Sinh slug không trùng: nếu đã có thì thêm hậu tố -2, -3, ...
    /// Kiểm tra cả bài đã xóa mềm để slug cũ không bị dùng lại.
    /// </summary>
    private async Task<string> GenerateUniqueSlugAsync(string title)
    {
        var baseSlug = SlugHelper.ToSlug(title);
        var slug = baseSlug;
        for (var i = 2; await _mongo.Posts.Find(p => p.Slug == slug).AnyAsync(); i++)
            slug = $"{baseSlug}-{i}";

        return slug;
    }
}
