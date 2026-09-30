using NewsCacheSession.Api.Models;

namespace NewsCacheSession.Api.DTOs.Categories;

public class CategoryResponse
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string? Description { get; set; }

    public static CategoryResponse FromModel(Category category) => new()
    {
        Id = category.Id,
        Name = category.Name,
        Slug = category.Slug,
        Description = category.Description
    };
}
