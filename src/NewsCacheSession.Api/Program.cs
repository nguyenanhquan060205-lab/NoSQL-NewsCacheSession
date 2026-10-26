using System.Text.Json;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using MongoDB.Driver;
using NewsCacheSession.Api.Data;
using NewsCacheSession.Api.HealthChecks;
using NewsCacheSession.Api.Middleware;
using NewsCacheSession.Api.Services;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// CORS — cho phép frontend gọi API
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

// Render/Vercel kết thúc HTTPS ở proxy rồi chuyển vào container bằng HTTP kèm X-Forwarded-Proto.
// Đọc header này để Request.IsHttps đúng → cookie SessionId có cờ Secure trên bản deploy.
// IP proxy của Render không cố định nên tin header từ mọi nguồn; app không dùng IP client cho
// phân quyền, giả mạo header chỉ làm cookie thêm/bớt cờ Secure. Chạy local không có header → không đổi gì.
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedProto;
    options.KnownNetworks.Clear();
    options.KnownProxies.Clear();
});

// Mongo
builder.Services.Configure<MongoSettings>(builder.Configuration.GetSection("MongoSettings"));
builder.Services.AddSingleton<MongoContext>();

// Redis (với AbortOnConnectFail = false để tăng độ bền kết nối)
var redisConnectionString = builder.Configuration.GetSection("RedisSettings")["ConnectionString"] ?? "localhost:6379";
var redisConfig = ConfigurationOptions.Parse(redisConnectionString);
redisConfig.AbortOnConnectFail = false;
builder.Services.AddSingleton<IConnectionMultiplexer>(ConnectionMultiplexer.Connect(redisConfig));

builder.Services.AddScoped<ICacheService, RedisCacheService>();
builder.Services.AddScoped<ISessionService, RedisSessionService>();
builder.Services.AddScoped<ISessionQueryService, RedisSessionQueryService>();
builder.Services.AddScoped<ICurrentUserService, CurrentUserService>();
builder.Services.Configure<CloudinarySettings>(builder.Configuration.GetSection("CloudinarySettings"));
builder.Services.AddHttpClient<IImageStorageService, CloudinaryImageStorageService>();

// Tạo index MongoDB lúc khởi động (posts.slug, users.username, categories.slug) — xem docs/mongodb-schema.md
builder.Services.AddHostedService<MongoIndexInitializer>();

// Worker định kỳ flush bộ đếm lượt xem từ Redis về MongoDB (Write-Behind - SCRUM-25)
builder.Services.AddHostedService<ViewCountSyncWorker>();

// Health Checks (MongoDB & Redis)
builder.Services.AddHealthChecks()
    .AddCheck<MongoHealthCheck>("mongodb", tags: new[] { "db", "nosql" })
    .AddCheck<RedisHealthCheck>("redis", tags: new[] { "cache", "nosql" });

var app = builder.Build();

app.UseForwardedHeaders(); // trước mọi middleware đọc Request.Scheme

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors();
app.UseSessionAuth(); // Middleware xác thực session qua Redis
app.UseAuthorization();

// Endpoint /health trả về JSON chi tiết
app.MapHealthChecks("/health", new HealthCheckOptions
{
    ResponseWriter = async (context, report) =>
    {
        context.Response.ContentType = "application/json";
        var result = JsonSerializer.Serialize(new
        {
            status = report.Status.ToString(),
            totalDuration = report.TotalDuration.ToString(),
            entries = report.Entries.ToDictionary(
                e => e.Key,
                e => new
                {
                    status = e.Value.Status.ToString(),
                    description = e.Value.Description,
                    duration = e.Value.Duration.ToString(),
                    error = e.Value.Exception?.Message
                })
        }, new JsonSerializerOptions { WriteIndented = true });

        await context.Response.WriteAsync(result);
    }
});

app.MapControllers();
app.Run();
