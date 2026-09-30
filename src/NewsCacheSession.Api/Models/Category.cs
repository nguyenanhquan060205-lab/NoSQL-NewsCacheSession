using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace NewsCacheSession.Api.Models;

/// <summary>
/// Chuyên mục tin tức trong collection "categories" (tên field camelCase).
/// Post tham chiếu tới đây qua Post.CategoryId.
/// </summary>
public class Category
{
    [BsonId]
    [BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = string.Empty;

    [BsonElement("name")]
    public string Name { get; set; } = string.Empty;

    [BsonElement("slug")]
    public string Slug { get; set; } = string.Empty;

    [BsonElement("description")]
    public string? Description { get; set; }

    [BsonElement("createdAt")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
