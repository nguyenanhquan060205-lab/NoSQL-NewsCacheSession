using MongoDB.Driver;
using NewsCacheSession.Api.Data;
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

// Redis
var redisConnectionString = builder.Configuration.GetSection("RedisSettings")["ConnectionString"];
builder.Services.AddSingleton<IConnectionMultiplexer>(
    ConnectionMultiplexer.Connect(redisConnectionString!));

builder.Services.AddScoped<ICacheService, RedisCacheService>();
builder.Services.AddScoped<ISessionService, RedisSessionService>();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors();
app.UseSessionAuth(); // Middleware xác thực session qua Redis
app.UseAuthorization();
app.MapControllers();
app.Run();
