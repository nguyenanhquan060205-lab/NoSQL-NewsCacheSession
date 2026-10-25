using System.Net;
using FluentAssertions;
using NewsCacheSession.Tests.Integration.Infrastructure;
using StackExchange.Redis;

namespace NewsCacheSession.Tests.Integration;

/// <summary>
/// Vòng đời Hash <c>session:{id}</c> trên Redis thật: tạo, trượt TTL, hết hạn, thu hồi.
/// </summary>
[Collection(IntegrationCollection.Name)]
public class SessionLifecycleTests : IAsyncLifetime
{
    private readonly NewsApiFactory _factory;

    public SessionLifecycleTests(NewsApiFactory factory) => _factory = factory;

    public Task InitializeAsync() => _factory.ResetAsync();
    public Task DisposeAsync() => Task.CompletedTask;

    private static RedisKey Key(string sessionId) => $"session:{sessionId}";

    [IntegrationFact]
    public async Task Login_ShouldCreateHashWithAllFiveFieldsAndTtlUpTo1800()
    {
        var (_, sessionId, userId) = await _factory.SignInNewUserAsync("admin_dau_tien");

        (await _factory.Redis.KeyTypeAsync(Key(sessionId))).Should().Be(RedisType.Hash);
        var fields = (await _factory.Redis.HashGetAllAsync(Key(sessionId)))
            .ToDictionary(e => e.Name.ToString(), e => e.Value.ToString());
        fields.Keys.Should().BeEquivalentTo(new[] { "userId", "username", "role", "loginAt", "lastActive" });
        fields["userId"].Should().Be(userId);
        fields["role"].Should().Be("admin");
        var ttl = await _factory.Redis.KeyTimeToLiveAsync(Key(sessionId));
        ttl!.Value.TotalSeconds.Should().BeInRange(1790, 1800);
    }

    [IntegrationFact]
    public async Task Request_WithCookieAfterTtlDropped_ShouldSlideTtlBackAndUpdateLastActive()
    {
        var (client, sessionId, _) = await _factory.SignInNewUserAsync("truot_ttl");
        await _factory.Redis.KeyExpireAsync(Key(sessionId), TimeSpan.FromSeconds(100));
        await _factory.Redis.HashSetAsync(Key(sessionId), "lastActive", "1000");

        (await client.GetAsync("/api/posts")).StatusCode.Should().Be(HttpStatusCode.OK);

        var ttl = await _factory.Redis.KeyTimeToLiveAsync(Key(sessionId));
        ttl!.Value.TotalSeconds.Should().BeGreaterThan(1790);
        ((string?)await _factory.Redis.HashGetAsync(Key(sessionId), "lastActive")).Should().NotBe("1000");
    }

    [IntegrationFact]
    public async Task Request_WithCookieAfterSliding_ShouldReissueCookieWithFreshMaxAge()
    {
        var (client, _, _) = await _factory.SignInNewUserAsync("cookie_truot");

        var response = await client.GetAsync("/api/auth/me");

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        response.Headers.TryGetValues("Set-Cookie", out var cookies).Should().BeTrue(
            "TTL trên Redis trượt thì cookie cũng phải được cấp lại, nếu không trình duyệt tự xóa cookie sau 30 phút kể từ lúc đăng nhập");
        cookies!.Should().Contain(c => c.StartsWith("SessionId=") && c.ToLowerInvariant().Contains("max-age=1800"));
    }

    [IntegrationFact]
    public async Task Request_AfterSessionExpired_ShouldReturn401AndNotRecreateOrphanHash()
    {
        var (client, sessionId, _) = await _factory.SignInNewUserAsync("het_han");
        await _factory.Redis.KeyExpireAsync(Key(sessionId), TimeSpan.FromSeconds(1));
        await Task.Delay(TimeSpan.FromSeconds(2));

        var me = await client.GetAsync("/api/auth/me");

        me.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        (await _factory.Redis.KeyExistsAsync(Key(sessionId))).Should().BeFalse("không được tạo lại Hash không TTL");
    }

    [IntegrationFact]
    public async Task RevokeSession_AdminRevokesUser_UserBecomes401_SelfRevoke400_RegularUser403()
    {
        var (admin, adminSession, _) = await _factory.SignInNewUserAsync("admin_dau_tien");
        var (user, userSession, _) = await _factory.SignInNewUserAsync("nguoi_thuong");

        var byUser = await user.DeleteAsync($"/api/auth/sessions/{adminSession}");
        var self = await admin.DeleteAsync($"/api/auth/sessions/{adminSession}");
        var revoke = await admin.DeleteAsync($"/api/auth/sessions/{userSession}");

        byUser.StatusCode.Should().Be(HttpStatusCode.Forbidden);
        self.StatusCode.Should().Be(HttpStatusCode.BadRequest);
        revoke.StatusCode.Should().Be(HttpStatusCode.NoContent);
        (await user.GetAsync("/api/auth/me")).StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        (await _factory.Redis.KeyExistsAsync(Key(userSession))).Should().BeFalse();
    }

    [IntegrationFact]
    public async Task GetActiveSessions_WithThreeSessions_ShouldListAllWithTtl()
    {
        var (admin, adminSession, _) = await _factory.SignInNewUserAsync("admin_dau_tien");
        await _factory.SignInNewUserAsync("nguoi_a");
        await _factory.SignInNewUserAsync("nguoi_b");

        var response = await admin.GetAsync("/api/auth/sessions");

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var items = (await NewsApiFactory.ReadJsonAsync(response)).EnumerateArray().ToList();
        items.Should().HaveCount(3);
        items.Should().OnlyContain(s => s.GetProperty("expiresInSeconds").GetInt64() > 1700);
        items.Single(s => s.GetProperty("isCurrent").GetBoolean()).GetProperty("sessionId").GetString().Should().Be(adminSession);
    }

    [IntegrationFact]
    public async Task Login_WithConfiguredTtl_ShouldUseSessionSettingsForHashAndCookie()
    {
        await using var factory = new NewsApiFactory(mongoUri: null, redisEndpoint: null, sessionTtlMinutes: 15);
        await factory.ResetAsync();
        var client = factory.CreateClient();
        var password = NewsApiFactory.NewPassword();
        await NewsApiFactory.RegisterAsync(client, "ttl_cau_hinh", password);

        var response = await client.PostAsync("/api/auth/login", System.Net.Http.Json.JsonContent.Create(
            new { username = "ttl_cau_hinh", password }));
        var sessionId = (await NewsApiFactory.ReadJsonAsync(response)).GetProperty("sessionId").GetString()!;

        var ttl = await factory.Redis.KeyTimeToLiveAsync(Key(sessionId));
        ttl!.Value.TotalSeconds.Should().BeInRange(890, 900, "SessionSettings:TtlMinutes = 15");
        response.Headers.GetValues("Set-Cookie").Single(c => c.StartsWith("SessionId="))
            .ToLowerInvariant().Should().Contain("max-age=900");
    }
}
