using Microsoft.AspNetCore.Mvc;
using MongoDB.Bson;
using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Categories;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Api.Services;
using NewsCacheSession.Api.Utils;

namespace NewsCacheSession.Api.Controllers;

/// <summary>
/// API chuyên mục tin tức. Đọc thì công khai (frontend cần render menu và dropdown chọn
/// chuyên mục khi soạn bài); tạo mới thì chỉ admin.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class CategoriesController : ControllerBase
{
    private readonly MongoContext _mongo;
    private readonly ICurrentUserService _currentUser;

    public CategoriesController(MongoContext mongo, ICurrentUserService currentUser)
    {
        _mongo = mongo;
        _currentUser = currentUser;
    }

    // Lấy qua MongoContext.Database để không phải sửa MongoContext.cs (file dùng chung).
    private IMongoCollection<Category> Categories => _mongo.Database.GetCollection<Category>("categories");

    /// <summary>
    /// Danh sách toàn bộ chuyên mục, sắp theo tên.
    /// </summary>
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        var categories = await Categories.Find(FilterDefinition<Category>.Empty)
            .SortBy(c => c.Name)
            .ToListAsync();

        return Ok(categories.Select(CategoryResponse.FromModel).ToList());
    }

    /// <summary>
    /// Chi tiết một chuyên mục theo ID.
    /// </summary>
    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(string id)
    {
        if (!ObjectId.TryParse(id, out _))
            return BadRequest(new { message = "ID chuyên mục không hợp lệ." });

        var category = await Categories.Find(c => c.Id == id).FirstOrDefaultAsync();
        if (category == null)
            return NotFound(new { message = "Chuyên mục không tồn tại." });

        return Ok(CategoryResponse.FromModel(category));
    }

    /// <summary>
    /// Chi tiết một chuyên mục theo slug (URL thân thiện: /chuyen-muc/the-thao).
    /// </summary>
    [HttpGet("slug/{slug}")]
    public async Task<IActionResult> GetBySlug(string slug)
    {
        var category = await Categories.Find(c => c.Slug == slug.ToLowerInvariant()).FirstOrDefaultAsync();
        if (category == null)
            return NotFound(new { message = "Chuyên mục không tồn tại." });

        return Ok(CategoryResponse.FromModel(category));
    }

    /// <summary>
    /// Tạo chuyên mục mới — chỉ admin. Slug sinh tự động từ tên.
    /// </summary>
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateCategoryRequest request)
    {
        var current = await _currentUser.GetAsync(HttpContext);
        if (current == null)
            return Unauthorized(new { message = "Bạn cần đăng nhập để tạo chuyên mục." });

        if (!current.IsAdmin)
            return StatusCode(StatusCodes.Status403Forbidden,
                new { message = "Chỉ quản trị viên tạo được chuyên mục." });

        var name = request.Name.Trim();
        if (string.IsNullOrEmpty(name))
            return BadRequest(new { message = "Tên chuyên mục không được để trống." });

        var category = new Category
        {
            Name = name,
            Slug = SlugHelper.ToSlug(name, fallback: "chuyen-muc"),
            Description = string.IsNullOrWhiteSpace(request.Description) ? null : request.Description.Trim(),
            CreatedAt = DateTime.UtcNow
        };

        try
        {
            await Categories.InsertOneAsync(category);
        }
        catch (MongoWriteException ex) when (ex.WriteError?.Category == ServerErrorCategory.DuplicateKey)
        {
            // unique index categories.slug — hai chuyên mục cùng tên sinh ra cùng slug.
            return Conflict(new { message = $"Chuyên mục với slug \"{category.Slug}\" đã tồn tại." });
        }

        return CreatedAtAction(nameof(GetById), new { id = category.Id }, CategoryResponse.FromModel(category));
    }
}
