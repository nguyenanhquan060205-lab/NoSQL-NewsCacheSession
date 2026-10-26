using System.ComponentModel.DataAnnotations;

namespace NewsCacheSession.Api.DTOs.Posts;

public class CreatePostRequest
{
    // Tiêu đề dài nhất trong dữ liệu hiện có là 110 ký tự.
    [Required]
    [MaxLength(300, ErrorMessage = "Tiêu đề tối đa 300 ký tự.")]
    public string Title { get; set; } = string.Empty;

    // Bài dài nhất hiện có 275 018 ký tự; chặn trên để một request không đẩy được hàng chục MB vào MongoDB và Redis.
    [Required]
    [MaxLength(500_000, ErrorMessage = "Nội dung tối đa 500 000 ký tự.")]
    public string Content { get; set; } = string.Empty;

    public string? ImageUrl { get; set; }

    public string? ImagePublicId { get; set; }

    /// <summary>ObjectId của chuyên mục (tuỳ chọn).</summary>
    public string? CategoryId { get; set; }
}
