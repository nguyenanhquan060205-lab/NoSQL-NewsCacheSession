using Microsoft.Extensions.Options;
using MongoDB.Driver;
using NewsCacheSession.Api.Models;

namespace NewsCacheSession.Api.Data;

public class MongoSettings
{
    public string ConnectionString { get; set; } = string.Empty;
    public string DatabaseName { get; set; } = string.Empty;
}

public class MongoContext
{
    private readonly IMongoDatabase _database;

    public MongoContext(IOptions<MongoSettings> settings)
    {
        var client = new MongoClient(settings.Value.ConnectionString);
        _database = client.GetDatabase(settings.Value.DatabaseName);
    }

    public IMongoDatabase Database => _database;
    public IMongoCollection<Post> Posts => _database.GetCollection<Post>("posts");
    public IMongoCollection<User> Users => _database.GetCollection<User>("users");
}
