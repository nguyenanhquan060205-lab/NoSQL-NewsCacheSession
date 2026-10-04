# MongoDB & C# Driver Development Guidelines

Hướng dẫn lập trình MongoDB.Driver chuẩn mực cho dự án NoSQL-NewsCacheSession.

---

## 1. Quy Chuẩn Đặt Tên Field (BSON camelCase)

Tất cả field trong MongoDB đều tuân theo quy tắc **camelCase**. Do C# đặt tên thuộc tính theo PascalCase, mọi Model **bắt buộc** phải khai báo `[BsonElement("...")]`:

```csharp
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

    [BsonElement("categoryId")]
    [BsonRepresentation(BsonType.ObjectId)]
    public string CategoryId { get; set; } = string.Empty;

    [BsonElement("authorId")]
    [BsonRepresentation(BsonType.ObjectId)]
    public string? AuthorId { get; set; }

    [BsonElement("views")]
    public long Views { get; set; } = 0;

    [BsonElement("isDeleted")]
    public bool IsDeleted { get; set; } = false;

    [BsonElement("createdAt")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [BsonElement("updatedAt")]
    public DateTime? UpdatedAt { get; set; }
}
```

> ⚠️ **Cảnh báo**: Nếu quên `[BsonElement("...")]`, C# driver sẽ lưu tên field dạng PascalCase (`Title`, `CreatedAt`). Việc này làm sai lệch dữ liệu và khiến các script Python/Seed data không thể đọc hoặc ghi đè đúng field.

---

## 2. Quản Lý Index (MongoIndexInitializer)

Đảm bảo các index quan trọng luôn được tạo khi ứng dụng khởi động:

1. **Posts**:
   - `slug`: Unique index trên các bài chưa xóa (`isDeleted: false`).
   - `categoryId` + `createdAt`: Compound index cho truy vấn danh sách phân trang theo chuyên mục.
   - `title`: Text index để phục vụ tìm kiếm.
2. **Users**:
   - `username`: Unique index.
   - `email`: Unique index.
3. **Categories**:
   - `slug`: Unique index.

---

## 3. Truy Vấn Phân Trang & Lọc (Pagination & Filter)

Sử dụng `FilterDefinition` và `FindOptions`:

```csharp
var filterBuilder = Builders<Post>.Filter;
var filter = filterBuilder.Eq(x => x.IsDeleted, false);

if (!string.IsNullOrEmpty(categoryId))
{
    filter &= filterBuilder.Eq(x => x.CategoryId, categoryId);
}

var totalItems = await _posts.CountDocumentsAsync(filter);
var items = await _posts.Find(filter)
    .SortByDescending(x => x.CreatedAt)
    .Skip((page - 1) * pageSize)
    .Limit(pageSize)
    .ToListAsync();
```
