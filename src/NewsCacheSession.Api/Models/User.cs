using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace NewsCacheSession.Api.Models;

/// <summary>
/// Tài khoản người dùng trong collection "users" (tên field camelCase).
/// </summary>
public class User
{
    [BsonId]
    [BsonRepresentation(BsonType.ObjectId)]
    public string Id { get; set; } = string.Empty;

    [BsonElement("username")]
    public string Username { get; set; } = string.Empty;

    [BsonElement("passwordHash")]
    public string PasswordHash { get; set; } = string.Empty;

    /// <summary>"admin" hoặc "user" — dùng cho trang quản trị (SCRUM-29).</summary>
    [BsonElement("role")]
    public string Role { get; set; } = UserRoles.User;

    [BsonElement("createdAt")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public static class UserRoles
{
    public const string Admin = "admin";
    public const string User = "user";
}
