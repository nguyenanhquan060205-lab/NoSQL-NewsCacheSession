using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using MongoDB.Driver;
using NewsCacheSession.Api.Models;
using NewsCacheSession.Tests.Integration.Infrastructure;

namespace NewsCacheSession.Tests.Integration;

/// <summary>
/// Luồng đăng ký / đăng nhập / đăng xuất của SV1 đi qua HTTP thật tới MongoDB + Redis thật.
/// </summary>
[Collection(IntegrationCollection.Name)]
public class AuthFlowTests : IAsyncLifetime
{
    private readonly NewsApiFactory _factory;

    public AuthFlowTests(NewsApiFactory factory) => _factory = factory;

    public Task InitializeAsync() => _factory.ResetAsync();
    public Task DisposeAsync() => Task.CompletedTask;

    [IntegrationFact]
    public async Task Register_FirstUserIsAdmin_SecondUserIsRegularUser()
    {
        var client = _factory.CreateClient();

        var first = await NewsApiFactory.RegisterAsync(client, "admin_dau_tien", NewsApiFactory.NewPassword());
        var second = await NewsApiFactory.RegisterAsync(client, "nguoi_thu_hai", NewsApiFactory.NewPassword());

        first.StatusCode.Should().Be(HttpStatusCode.Created);
        (await NewsApiFactory.ReadJsonAsync(first)).GetProperty("role").GetString().Should().Be(UserRoles.Admin);
        second.StatusCode.Should().Be(HttpStatusCode.Created);
        (await NewsApiFactory.ReadJsonAsync(second)).GetProperty("role").GetString().Should().Be(UserRoles.User);
    }

    [IntegrationFact]
    public async Task Register_StoresBcryptHashWithCamelCaseFields_NotPlainPassword()
    {
        var password = NewsApiFactory.NewPassword();
        await NewsApiFactory.RegisterAsync(_factory.CreateClient(), "kiem_tra_hash", password);

        var raw = await _factory.Mongo.GetCollection<MongoDB.Bson.BsonDocument>("users")
            .Find(FilterDefinition<MongoDB.Bson.BsonDocument>.Empty).SingleAsync();

        raw.Names.Should().Contain(new[] { "username", "passwordHash", "role", "createdAt" });
        raw["passwordHash"].AsString.Should().StartWith("$2").And.NotContain(password);
    }

    [IntegrationFact]
    public async Task Register_DuplicateUsername_ShouldReturn409()
    {
        var client = _factory.CreateClient();
        await NewsApiFactory.RegisterAsync(client, "trung_ten", NewsApiFactory.NewPassword());

        var again = await NewsApiFactory.RegisterAsync(client, "trung_ten", NewsApiFactory.NewPassword());

        again.StatusCode.Should().Be(HttpStatusCode.Conflict);
    }

    [IntegrationFact]
    public async Task Login_WithCorrectCredentials_ShouldSetHttpOnlySessionCookieAndReturnSessionId()
    {
        var client = _factory.CreateClient();
        var password = NewsApiFactory.NewPassword();
        await NewsApiFactory.RegisterAsync(client, "dang_nhap_dung", password);

        var response = await client.PostAsJsonAsync("/api/auth/login", new { username = "dang_nhap_dung", password });

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var sessionId = (await NewsApiFactory.ReadJsonAsync(response)).GetProperty("sessionId").GetString();
        sessionId.Should().NotBeNullOrEmpty();

        var setCookie = response.Headers.GetValues("Set-Cookie").Single(c => c.StartsWith("SessionId="));
        setCookie.Should().Contain($"SessionId={sessionId}");
        setCookie.ToLowerInvariant().Should().Contain("httponly").And.Contain("samesite=lax").And.Contain("max-age=1800");
    }

    [IntegrationFact]
    public async Task Login_WrongPasswordAndUnknownUsername_ShouldReturnSame401Message()
    {
        var client = _factory.CreateClient();
        await NewsApiFactory.RegisterAsync(client, "co_that", NewsApiFactory.NewPassword());

        var wrongPassword = await client.PostAsJsonAsync("/api/auth/login", new { username = "co_that", password = "sai-mat-khau" });
        var unknownUser = await client.PostAsJsonAsync("/api/auth/login", new { username = "khong_ton_tai", password = "sai-mat-khau" });

        wrongPassword.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        unknownUser.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        (await wrongPassword.Content.ReadAsStringAsync()).Should().Be(await unknownUser.Content.ReadAsStringAsync());
        _factory.RedisKeys("session:*").Should().BeEmpty("đăng nhập sai không được tạo phiên");
    }

    [IntegrationFact]
    public async Task Me_AfterLogin_ShouldReturn200WithTtlNear1800_AndAfterLogout401()
    {
        var (client, sessionId, _) = await _factory.SignInNewUserAsync("hoi_me");

        var me = await client.GetAsync("/api/auth/me");
        me.StatusCode.Should().Be(HttpStatusCode.OK);
        (await NewsApiFactory.ReadJsonAsync(me)).GetProperty("expiresInSeconds").GetInt64().Should().BeInRange(1790, 1800);

        var logout = await client.PostAsync("/api/auth/logout", null);
        logout.StatusCode.Should().Be(HttpStatusCode.OK);

        (await client.GetAsync("/api/auth/me")).StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        (await _factory.Redis.KeyExistsAsync($"session:{sessionId}")).Should().BeFalse();
    }

    [IntegrationFact]
    public async Task Register_TenParallelFirstRegistrationsOnEmptyDb_ShouldCreateExactlyOneAdmin()
    {
        var client = _factory.CreateClient();

        var responses = await Task.WhenAll(Enumerable.Range(1, 10)
            .Select(i => NewsApiFactory.RegisterAsync(client, $"chen_nhau_{i}", NewsApiFactory.NewPassword())));

        responses.Should().OnlyContain(r => r.StatusCode == HttpStatusCode.Created);
        var admins = await _factory.Users.CountDocumentsAsync(u => u.Role == UserRoles.Admin);
        admins.Should().Be(1, "chỉ người đăng ký đầu tiên được làm admin, kể cả khi các request chen nhau");
    }

    [IntegrationFact]
    public async Task Register_OverlongUsernameOrPassword_ShouldReturn400()
    {
        var client = _factory.CreateClient();

        var longUsername = await NewsApiFactory.RegisterAsync(client, new string('u', 51), NewsApiFactory.NewPassword());
        // BCrypt chỉ dùng 72 byte đầu: hai mật khẩu chung 72 byte đầu sẽ cùng đăng nhập được.
        var longPassword = await NewsApiFactory.RegisterAsync(client, "mat_khau_dai", new string('p', 73));

        longUsername.StatusCode.Should().Be(HttpStatusCode.BadRequest);
        longPassword.StatusCode.Should().Be(HttpStatusCode.BadRequest);
    }
}
