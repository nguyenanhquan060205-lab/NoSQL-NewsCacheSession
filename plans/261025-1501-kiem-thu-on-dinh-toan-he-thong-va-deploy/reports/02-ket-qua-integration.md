# Phase 2 — Kết quả integration test backend thật (26/10/2026)

Chạy trên nhánh `develop` (`9665335` + test mới), container QA Mongo `:27019` / Redis `:6380` (DB 15).

```bash
NEWS_IT=1 dotnet test --filter "FullyQualifiedName~Integration"   # 41 test: 34 pass, 7 fail (đúng chỗ có lỗi)
dotnet test                                                       # 25 pass, 39 skipped — không cần Docker
```

## Hạ tầng test

| File | Vai trò |
|---|---|
| `Integration/Infrastructure/NewsApiFactory.cs` | `WebApplicationFactory<HealthController>` — **không** phải sửa `Program.cs`. Đặt biến môi trường ngay trong `CreateHost` (trước khi `Program` đọc chuỗi Redis), ép `defaultDatabase=15`, DB Mongo `newsdb_it_{guid}` drop khi dispose, `ResetAsync()` FLUSHDB + xóa document trước mỗi test |
| `Integration/Infrastructure/IntegrationFactAttribute.cs` | Skip khi thiếu `NEWS_IT=1`; một `[Collection("Integration")]` để chạy tuần tự |
| Gói thêm | `Microsoft.AspNetCore.Mvc.Testing 10.0.11` (khớp runtime 10.0.11 của máy, test `net10.0`, API `net8.0` + `RollForward=Major`) |

Spike bước 1 (`GET /health` qua factory): pass ngay sau khi chuyển constructor có tham số sang `internal`
(xUnit chỉ cho collection fixture một constructor public).

## Kết quả theo bảng của plan

### Flow Như (SV1)

| Test | Kết quả |
|---|---|
| `AuthFlowTests.Register_FirstUserIsAdmin_SecondUserIsRegularUser` | ✅ |
| `AuthFlowTests.Register_StoresBcryptHashWithCamelCaseFields_NotPlainPassword` | ✅ |
| `AuthFlowTests.Register_DuplicateUsername_ShouldReturn409` | ✅ |
| `AuthFlowTests.Login_WithCorrectCredentials_ShouldSetHttpOnlySessionCookieAndReturnSessionId` | ✅ `HttpOnly; SameSite=Lax; Max-Age=1800` |
| `AuthFlowTests.Login_WrongPasswordAndUnknownUsername_ShouldReturnSame401Message` | ✅ cùng body, không tạo phiên |
| `AuthFlowTests.Me_AfterLogin_ShouldReturn200WithTtlNear1800_AndAfterLogout401` | ✅ |
| `AuthFlowTests.Register_TenParallelFirstRegistrationsOnEmptyDb_ShouldCreateExactlyOneAdmin` | ❌ **G16** |
| `AuthFlowTests.Register_OverlongUsernameOrPassword_ShouldReturn400` | ❌ **G19** |
| `PostCrudFlowTests.Create_WithoutLogin_ShouldReturn401` | ✅ |
| `PostCrudFlowTests.Create_WithValidCategory_ShouldStoreVietnameseSlugAndObjectIdReferences` | ✅ `duong-pho-ha-noi-mua-thu`, `categoryId`/`authorId` là ObjectId |
| `PostCrudFlowTests.Create_WithMalformedOrUnknownCategory_ShouldReturn400` | ✅ |
| `PostCrudFlowTests.Create_TwoPostsWithSameTitleSequentially_ShouldSuffixSecondSlug` | ✅ `-2` |
| `PostCrudFlowTests.Create_TenParallelPostsWithSameTitle_ShouldNeverReturn500` | ❌ **G15** |
| `PostCrudFlowTests.Create_OverlongTitle_ShouldReturn400` | ❌ **G19** |
| `PostCrudFlowTests.UpdateAndDelete_SeedPostByRegularUser_ShouldReturn403AndKeepCache` | ✅ cache còn nguyên |
| `PostCrudFlowTests.Update_AuthorEditsOwnPost_AndAdminEditsAnyPost_ShouldReturn200` | ✅ |
| `PostCrudFlowTests.Delete_ShouldSoftDeleteInMongoAndHideFromApi` | ✅ `isDeleted=true`, `deletedAt` kiểu Date |
| `PostCrudFlowTests.GetAll_ShouldPaginateFilterByCategoryAndClampPageSize` | ✅ trang 2 bắt đầu "Bài 49", lọc 15 bài, `pageSize=500` → 50 |

### Flow Quân (SV2)

| Test | Kết quả |
|---|---|
| `CacheInvalidationTests.GetById_FirstThenSecondCall_ShouldMissThenHitAndStoreStringWithTtl` | ✅ String, TTL 1–600 |
| `CacheInvalidationTests.Update_ShouldDeleteCacheKeyBumpListVersionAndNextGetMissesWithNewTitle` | ✅ |
| `CacheInvalidationTests.Delete_ShouldDeleteCacheKeyButKeepViewCounter` | ✅ |
| `CacheInvalidationTests.GetBySlug_ShouldNotCreateAnyPostCacheKey` | ✅ |
| `CacheInvalidationTests.GetAll_HitAfterFirstCall_ThenMissWithNewPostFirstAfterCreate` | ✅ 2 key `posts:cat:all:p1:v0`, `…:v1` |
| `CacheInvalidationTests.GetById_FiftyParallelRequestsOnColdKey_ShouldMissExactlyOnceAndReleaseLock` | ✅ 1 MISS / 49 HIT, không còn `lock:post:{id}` |
| `SessionLifecycleTests.Login_ShouldCreateHashWithAllFiveFieldsAndTtlUpTo1800` | ✅ |
| `SessionLifecycleTests.Request_WithCookieAfterTtlDropped_ShouldSlideTtlBackAndUpdateLastActive` | ✅ |
| `SessionLifecycleTests.Request_AfterSessionExpired_ShouldReturn401AndNotRecreateOrphanHash` | ✅ |
| `SessionLifecycleTests.RevokeSession_AdminRevokesUser_UserBecomes401_SelfRevoke400_RegularUser403` | ✅ |
| `SessionLifecycleTests.GetActiveSessions_WithThreeSessions_ShouldListAllWithTtl` | ✅ |
| `SessionLifecycleTests.Request_WithCookieAfterSliding_ShouldReissueCookieWithFreshMaxAge` | ❌ **G17** |
| `SessionLifecycleTests.Login_WithConfiguredTtl_ShouldUseSessionSettingsForHashAndCookie` | ❌ **G17** |
| `ViewCounterFlowTests.IncrementView_FirstViewOfPostWithMongoViews_ShouldContinueFromMongoValue` | ✅ 501 |
| `ViewCounterFlowTests.IncrementView_FiftyParallelViews_ShouldCountEveryOne` | ✅ 10 + 50 = 60 |
| `ViewCounterFlowTests.IncrementView_UnknownId_ShouldReturn404AndNotCreateCounter` | ✅ |
| `ViewCounterFlowTests.Flush_ShouldWriteRedisCounterToMongoAndEmptyDirtySet` | ✅ |
| `ViewCounterFlowTests.IncrementView_AfterRedisLostAllKeys_ShouldContinueFromFlushedMongoValue` | ✅ 104 (G13) |
| `ViewCounterFlowTests.IncrementView_SoftDeletedPostWithLiveCounter_StillCounts` | ✅ ghi lại hành vi G12 |
| `ViewCounterFlowTests.CacheStats_AfterOneMissAndOneHit_ShouldCountEachOnce` | ✅ hits=1, misses=1, 50% |
| `HealthEndpointTests.Health_WithMongoAndRedisUp_ShouldReportHealthyForBoth` | ✅ |

## Bằng chứng cho 7 test đỏ

```
G16  Expected admins to be 1L ... but found 10L (difference of 9).
G15  Expected codes {500, 500, 500, 201, 500, 500, 500, 500, 500, 500} to not contain 500
G19  Create_OverlongTitle:        Expected ... BadRequest {value: 400}, but found ... Created {value: 201}.
G19  Register_OverlongUsername:   Expected longUsername.StatusCode to be ... 400, but found ... 201.
G17  Reissue cookie:              Expected response.Headers.TryGetValues("Set-Cookie", ...) to be True ... but found False.
G17  Configured TTL (15 phút):    Expected ttl ... between 890.0 and 900.0 ... but found 1799.999.
```

G18 — `redis-cli MONITOR` trên Redis QA trong một lần đăng nhập admin (đã che ID):
```
"HMSET"  "session:<sid>" "userId" "<uid>" "username" "qa_admin" "role" "user" "loginAt" "<ts>" "lastActive" "<ts>"
"EXPIRE" "session:<sid>" "1800"
"HMSET"  "session:<sid>" "role" "admin" "lastActive" "<ts>"
```
Ba lệnh rời nhau: (1) admin có một khoảng `role=user`; (2) giữa HMSET và EXPIRE key **không có TTL** —
tiến trình chết đúng lúc đó thì Hash nằm vĩnh viễn trong Redis. Ý (2) nằm trong
`RedisSessionService.CreateSessionAsync` (file SV2) → sửa cùng N4 bằng MULTI/EXEC.

## Kết luận G8–G19

| # | Kết luận | Bằng chứng | Chủ file | Sửa ở Phase 5 |
|---|---|---|---|---|
| G8 | **Đúng** — test cũ gọi chính mock rồi verify mock | Đã viết lại `CacheInvalidationTests` thành 6 test thật, cả 6 xanh → invalidation thật sự chạy đúng | SV2 | Xong ở phase này |
| G9 | Chưa đo — Phase 4 | | SV2 | |
| G10 | Chưa đo — Phase 4 | | SV2 | |
| G11 | Chưa đo — Phase 4 | | SV2 | |
| G12 | **Đúng** (hành vi đã chấp nhận) | `IncrementView_SoftDeletedPostWithLiveCounter_StillCounts` → 200 | SV2 | Không sửa (đánh đổi hiệu năng) |
| G13 | **Đã sửa** ở `9665335`, chạy đúng | 501 với `views=500`; sau FLUSHDB đếm tiếp 104, Mongo không tụt | SV2 | — |
| G14 | Chưa đo — Phase 4 | | SV1 | |
| G15 | **Đúng** — 9/10 request 500 | `Create_TenParallelPostsWithSameTitle_ShouldNeverReturn500` | SV1 | N1 |
| G16 | **Đúng** — 10/10 thành admin | `Register_TenParallelFirstRegistrationsOnEmptyDb_ShouldCreateExactlyOneAdmin` | SV1 | N3 |
| G17 | **Đúng** cả hai ý: cookie không cấp lại khi trượt; TTL hardcode bỏ qua `SessionSettings:TtlMinutes` | 2 test đỏ ở trên | SV2 (cookie) + SV1 (TTL) | S4 + N4 |
| G18 | **Đúng** — 3 lệnh rời, có khoảng không TTL | `MONITOR` ở trên | SV1 + SV2 | N4 (+ MULTI trong `CreateSessionAsync`) |
| G19 | **Đúng** — tiêu đề 301 ký tự, username 51 ký tự, mật khẩu 73 byte đều 201 | 2 test đỏ ở trên | SV1 | N5 |

Không sửa code sản phẩm ở phase này. 7 test đỏ là đầu vào của Phase 5.
