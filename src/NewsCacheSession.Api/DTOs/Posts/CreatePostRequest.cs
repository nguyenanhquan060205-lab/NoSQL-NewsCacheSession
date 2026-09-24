using System.ComponentModel.DataAnnotations;

namespace NewsCacheSession.Api.DTOs.Posts;

public class CreatePostRequest
{
    [Required]
    public string Title { get; set; } = string.Empty;

    [Required]
    public string Content { get; set; } = string.Empty;

    public string? ImageUrl { get; set; }

    /// <summary>ObjectId của chuyên mục (tuỳ chọn).</summary>
    public string? CategoryId { get; set; }
}
