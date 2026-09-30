using Microsoft.AspNetCore.Mvc;
using MongoDB.Bson;
using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.DTOs.Categories;
using NewsCacheSession.Api.Models;

namespace NewsCacheSession.Api.Controllers;

/// <summary>
/// API chuyên mục tin tức — chỉ đọc. Frontend dùng để render menu và dropdown
/// chọn chuyên mục khi soạn bài; danh sách chuyên mục do script seed nạp.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class CategoriesController : ControllerBase
{
    private readonly MongoContext _mongo;

    public CategoriesController(MongoContext mongo)
    {
        _mongo = mongo;
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
    /// Chi tiết một chuyên mục theo slug (dùng cho URL thân thiện: /chuyen-muc/the-thao).
    /// </summary>
    [HttpGet("slug/{slug}")]
    public async Task<IActionResult> GetBySlug(string slug)
    {
        var category = await Categories.Find(c => c.Slug == slug.ToLowerInvariant()).FirstOrDefaultAsync();
        if (category == null)
            return NotFound(new { message = "Chuyên mục không tồn tại." });

        return Ok(CategoryResponse.FromModel(category));
    }
}
