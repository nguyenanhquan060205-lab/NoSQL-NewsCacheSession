namespace NewsCacheSession.Tests.Integration.Infrastructure;

/// <summary>
/// Test chạy trên Redis + MongoDB thật. Mặc định bị bỏ qua để <c>dotnet test</c> không cần Docker;
/// bật bằng biến môi trường <c>NEWS_IT=1</c> (xem <see cref="NewsApiFactory"/> để biết trỏ vào đâu).
/// </summary>
public sealed class IntegrationFactAttribute : FactAttribute
{
    public IntegrationFactAttribute()
    {
        if (!NewsApiFactory.Enabled)
            Skip = "Integration test cần NEWS_IT=1 và container QA (Mongo :27019, Redis :6380).";
    }
}

/// <summary>
/// Mọi lớp integration dùng chung một collection để chạy TUẦN TỰ: factory đặt biến môi trường
/// cho cả tiến trình, hai collection chạy song song sẽ ghi đè cấu hình của nhau.
/// </summary>
[CollectionDefinition(Name)]
public sealed class IntegrationCollection : ICollectionFixture<NewsApiFactory>
{
    public const string Name = "Integration";
}
