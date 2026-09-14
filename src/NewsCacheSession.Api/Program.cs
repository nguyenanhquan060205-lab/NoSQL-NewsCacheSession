using System.Text.Json;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
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

// Health Checks (MongoDB & Redis)
builder.Services.AddHealthChecks()
    .AddCheck<MongoHealthCheck>("mongodb", tags: new[] { "db", "nosql" })
    .AddCheck<RedisHealthCheck>("redis", tags: new[] { "cache", "nosql" });

var app = builder.Build();

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
