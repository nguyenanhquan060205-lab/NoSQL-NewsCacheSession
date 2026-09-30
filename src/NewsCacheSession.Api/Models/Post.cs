using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace NewsCacheSession.Api.Models;

/// <summary>
/// Bài viết trong collection "posts".
/// Tên field trong MongoDB đặt camelCase (xem docs/mongodb-schema.md) để khớp với
/// script seed và JSON trả về cho frontend — không dựa vào tên property mặc định.
/// </summary>
public class Post
{
    [BsonId]
    [BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = string.Empty;

    [BsonElement("title")]
    public string Title { get; set; } = string.Empty;

    [BsonElement("slug")]
    public string Slug { get; set; } = string.Empty;

    [BsonElement("content")]
    public string Content { get; set; } = string.Empty;

    [BsonElement("imageUrl")]
    public string? ImageUrl { get; set; }

    /// <summary>ObjectId tham chiếu collection "categories".</summary>
    [BsonElement("categoryId")]
    [BsonRepresentation(BsonType.ObjectId)]
    public string? CategoryId { get; set; }

    /// <summary>ObjectId tham chiếu collection "users". Null với dữ liệu seed.</summary>
    [BsonElement("authorId")]
    [BsonRepresentation(BsonType.ObjectId)]
    public string? AuthorId { get; set; }

    /// <summary>
    /// Lượt xem đã được chốt vào MongoDB. Số đếm thời gian thực nằm ở Redis
    /// (key post:{id}:views, dùng INCR) và được job của SV2 flush ngược về đây.
    /// </summary>
    [BsonElement("views")]
    public int Views { get; set; } = 0;

    [BsonElement("isDeleted")]
    public bool IsDeleted { get; set; } = false;

    [BsonElement("deletedAt")]
    public DateTime? DeletedAt { get; set; }

    [BsonElement("createdAt")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [BsonElement("updatedAt")]
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
