using System.ComponentModel.DataAnnotations;

namespace NewsCacheSession.Api.DTOs.Posts;

public class UpdatePostRequest
{
    [Required]
    public string Title { get; set; } = string.Empty;

    [Required]
    public string Content { get; set; } = string.Empty;

    public string? ImageUrl { get; set; }
}
