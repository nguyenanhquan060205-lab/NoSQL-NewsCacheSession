using NewsCacheSession.Api.Models;

namespace NewsCacheSession.Api.DTOs.Posts;

public class PostResponse
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public string? ImageUrl { get; set; }
    public string? AuthorId { get; set; }
    public int Views { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public static PostResponse FromModel(Post post) => new()
    {
        Id = post.Id,
        Title = post.Title,
        Slug = post.Slug,
        Content = post.Content,
        ImageUrl = post.ImageUrl,
        AuthorId = post.AuthorId,
        Views = post.Views,
        CreatedAt = post.CreatedAt,
        UpdatedAt = post.UpdatedAt
    };
}
