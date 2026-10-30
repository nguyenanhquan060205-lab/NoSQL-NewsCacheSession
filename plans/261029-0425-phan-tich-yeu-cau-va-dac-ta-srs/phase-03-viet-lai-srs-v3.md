---
phase: 3
title: "Viết lại SRS v3.0 cho tới khi xanh"
status: complete
priority: P1
effort: "6h"
dependencies: [2]
---

# Phase 3: Viết lại SRS v3.0 cho tới khi xanh

## Goal

Viết lại `docs/SRS.md` thành v3.0 theo hợp đồng định dạng ở Phase 1, sửa đủ D1–D24, bổ sung phần
còn thiếu, cho tới khi `check_srs.py` thoát `0`.

## Context Links

- Kho yêu cầu + hợp đồng định dạng: `reports/01-phan-tich-yeu-cau.md`
- Kết quả đỏ: `reports/02-ket-qua-do-tren-v2.txt`
- Sai lệch + phần thiếu: [reports/00-scout-doi-chieu-tai-lieu-voi-code.md](./reports/00-scout-doi-chieu-tai-lieu-voi-code.md) §2, §3
- Nội dung đúng để dẫn, không chép lại: `docs/redis-keyspace.md`, `docs/mongodb-schema.md`,
  `docs/bao-cao-nguyen-ly-cache-aside.md`, `docs/bao-cao-kiem-thu-hieu-nang.md`

## Scout trước khi làm (deep mode)

1. `git log --oneline dd9d242..HEAD -- src tests scripts` — có đổi thì chạy lại
   `python3 scripts/DocCheck/check_srs.py --only C1,C2,C3,C5,C6` trên bản v2.0 để thấy chỗ mới lệch.
2. `git status docs/SRS.md` — chắc chắn không ai sửa SRS song song (so với `reports/srs-v2.0.md`).

## Key Insights

- Giữ nguyên ID FR-01…FR-21 của v2.0; thêm FR-22, IR-01…05, NFR-05…09, DR-01…03.
- Đề bài không cho điểm con ở phần 2 và phần 3 → ma trận barem chỉ ghi 2.5đ cho cả phần (D24).
- Số đo phải trung thực: MISS 8,74 ms, HIT 2,96 ms, không cache 3,66 ms. Kịch bản demo không được hứa
  "~150–200 ms" nữa. Thay bằng: header `X-Cache` đổi MISS → HIT, HIT ≤ 5 ms, kèm câu giải thích từ
  `docs/bao-cao-kiem-thu-hieu-nang.md` §5.2.
- Phụ lục A: 10.251 bài (10.150 chưa xóa), 7 chuyên mục — nguồn
  `plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/reports/03-e2e-va-dien-tap.md:60`. Phase 4 đo lại.
- `volatile-lru` chỉ có ở Redis Cloud bản deploy, không có ở `docker-compose.yml` local.

## Dàn ý SRS v3.0

```
Thông tin tài liệu · Lịch sử phiên bản (v2.0 → v3.0: liệt kê D1–D24 đã sửa)   ← vùng bỏ qua của checker
1. Giới thiệu
   1.1 Mục đích · 1.2 Phạm vi · 1.3 Thuật ngữ · 1.4 Tham chiếu (thêm ISO/IEC/IEEE 29148:2018)
   1.5 Quy ước: mã yêu cầu, mức ưu tiên BẮT BUỘC/NÊN/CÓ THỂ, phương pháp kiểm chứng T/D/I/A
   1.6 Yêu cầu nguồn từ đề bài: bảng DB-01…DB-19 trích nguyên văn
2. Mô tả tổng quan
   2.1 Kiến trúc (sửa sơ đồ: cookie SessionId, Cloudinary gọi từ ImagesController + PostsController)
       Môi trường: local (compose: mongo:7.0, redis:7-alpine, RedisInsight 5540) và deploy
       (Render + Atlas M0 + Redis Cloud volatile-lru + Vercel, dẫn docs/huong-dan-deploy.md)
   2.2 Chức năng · 2.3 Tác nhân · 2.4 Ràng buộc (camelCase, keyspace, ghi Mongo trước)
   2.5 Giả định (SDK 10 để chạy test, API net8.0) · 2.6 Phân công (DB-18, DB-19, AGENTS.md §4)
3. Yêu cầu cụ thể
   3.1 Giao diện: IR-01…IR-05 + giao diện phần mềm (phiên bản thật) + truyền thông
       (cookie SessionId HttpOnly/SameSite=Lax/Secure theo scheme/Max-Age = TTL; X-Session-Id; X-Cache)
   3.2 FR-01…FR-22 (mỗi khối: bảng thuộc tính, Mô tả "Hệ thống PHẢI…", Tiêu chí chấp nhận Cho/Khi/Thì)
   3.3 NFR-01…NFR-09 · 3.4 DR-01…DR-03 · 3.5 Thuộc tính hệ thống: trỏ về NFR-05…NFR-09
4. Phụ lục
   A Dummy data · B Số đo (bảng định dạng chuẩn, 5 đợt stampede, bảng tải 1/10/50 luồng)
   C Truy vết: C.1 DB → yêu cầu → TC; C.2 37 ticket (trạng thái CSV + bằng chứng repo)
   D Kịch bản demo 3 bước (RedisInsight http://localhost:5540, cookie SessionId, số đo thật)
   E Danh mục test case · F Vấn đề tài liệu nguồn và quyết định (S1–S10, D24)   ← vùng bỏ qua
   G Cách kiểm thử tài liệu (lệnh checker + unit test)
```

## Bản nháp danh mục test case (Phụ lục E) — xác minh tên method khi viết

Đường dẫn gốc `tests/NewsCacheSession.Tests/`. Checker C12 sẽ báo nếu tên sai.

| TC | Loại | Bằng chứng | Yêu cầu |
|---|---|---|---|
| TC-01 | T | `Integration/AuthFlowTests.cs::Register_FirstUserIsAdmin_SecondUserIsRegularUser` | FR-01 |
| TC-02 | T | `Integration/AuthFlowTests.cs::Register_TenParallelFirstRegistrationsOnEmptyDb_ShouldCreateExactlyOneAdmin` | FR-01 |
| TC-03 | T | `Integration/AuthFlowTests.cs::Register_StoresBcryptHashWithCamelCaseFields_NotPlainPassword` | FR-01, NFR-06, DR-01 |
| TC-04 | T | `Integration/AuthFlowTests.cs::Register_DuplicateUsername_ShouldReturn409` | FR-01 |
| TC-05 | T | `Integration/AuthFlowTests.cs::Register_OverlongUsernameOrPassword_ShouldReturn400` | FR-01 |
| TC-06 | T | `Integration/AuthFlowTests.cs::Login_WithCorrectCredentials_ShouldSetHttpOnlySessionCookieAndReturnSessionId` | FR-02, NFR-06 |
| TC-07 | T | `Integration/AuthFlowTests.cs::Login_WrongPasswordAndUnknownUsername_ShouldReturnSame401Message` | FR-02, NFR-06 |
| TC-08 | T | `Integration/SessionLifecycleTests.cs::Login_ShouldCreateHashWithAllFiveFieldsAndTtlUpTo1800` | FR-02, DR-02 |
| TC-09 | T | `Services/SessionServiceTests.cs::CreateSessionAsync_WithRole_ShouldStoreAllRequiredHashEntriesAndSetTtlInOneTransaction` | FR-02 |
| TC-10 | T | `Integration/SessionLifecycleTests.cs::Request_WithCookieAfterTtlDropped_ShouldSlideTtlBackAndUpdateLastActive` | FR-03 |
| TC-11 | T | `Integration/SessionLifecycleTests.cs::Request_WithCookieAfterSliding_ShouldReissueCookieWithFreshMaxAge` | FR-03 |
| TC-12 | T | `Integration/SessionLifecycleTests.cs::Request_AfterSessionExpired_ShouldReturn401AndNotRecreateOrphanHash` | FR-03 |
| TC-13 | T | `Middleware/SessionAuthMiddlewareTests.cs::InvokeAsync_WithValidCookieSession_ShouldPopulateItemsAndRefreshTtl` | FR-03 |
| TC-14 | T | `Integration/AuthFlowTests.cs::Me_AfterLogin_ShouldReturn200WithTtlNear1800_AndAfterLogout401` | FR-04, FR-22 |
| TC-15 | T | `Integration/SessionLifecycleTests.cs::RevokeSession_AdminRevokesUser_UserBecomes401_SelfRevoke400_RegularUser403` | FR-05 |
| TC-16 | T | `Integration/SessionLifecycleTests.cs::GetActiveSessions_WithThreeSessions_ShouldListAllWithTtl` | FR-05 |
| TC-17 | T | `Integration/PostCrudFlowTests.cs::Create_WithValidCategory_ShouldStoreVietnameseSlugAndObjectIdReferences` | FR-06, DR-01 |
| TC-18 | T | `Integration/PostCrudFlowTests.cs::Create_TenParallelPostsWithSameTitle_ShouldNeverReturn500` | FR-06 |
| TC-19 | T | `Integration/PostCrudFlowTests.cs::Create_WithMalformedOrUnknownCategory_ShouldReturn400` | FR-06 |
| TC-20 | T | `Integration/PostCrudFlowTests.cs::CreateAndUpload_WhenPostingIsAdminOnly_RegularUser403_AdminAllowed` | FR-06, FR-21 |
| TC-21 | T | `Integration/PostCrudFlowTests.cs::Update_AuthorEditsOwnPost_AndAdminEditsAnyPost_ShouldReturn200` | FR-07 |
| TC-22 | T | `Integration/PostCrudFlowTests.cs::UpdateAndDelete_SeedPostByRegularUser_ShouldReturn403AndKeepCache` | FR-07, FR-08 |
| TC-23 | T | `Integration/PostCrudFlowTests.cs::Delete_ShouldSoftDeleteInMongoAndHideFromApi` | FR-08 |
| TC-24 | T | `Integration/PostCrudFlowTests.cs::GetAll_ShouldPaginateFilterByCategoryAndClampPageSize` | FR-09, FR-11 |
| TC-25 | T | `Integration/CacheInvalidationTests.cs::GetBySlug_ShouldNotCreateAnyPostCacheKey` | FR-10 |
| TC-26 | T | `Integration/CacheInvalidationTests.cs::GetById_FirstThenSecondCall_ShouldMissThenHitAndStoreStringWithTtl` | FR-12, DR-02 |
| TC-27 | T | `Controllers/PostsControllerCacheAsideTests.cs::GetById_WhenCacheHit_ShouldReturnFromCacheWithHitHeaderAndNotQueryMongo` | FR-12 |
| TC-28 | T | `Integration/CacheInvalidationTests.cs::GetById_FiftyParallelRequestsOnColdKey_ShouldMissExactlyOnceAndReleaseLock` | FR-13, NFR-03 |
| TC-29 | T | `Integration/ResilienceTests.cs::GetById_WhileAnotherHolderKeepsLock_ShouldFallBackToMongoWithinBoundedWait` | FR-13 |
| TC-30 | T | `Integration/CacheInvalidationTests.cs::Update_ShouldDeleteCacheKeyBumpListVersionAndNextGetMissesWithNewTitle` | FR-07, FR-14, FR-16 |
| TC-31 | T | `Integration/CacheInvalidationTests.cs::Delete_ShouldDeleteCacheKeyButKeepViewCounter` | FR-08, FR-14 |
| TC-32 | T | `Integration/ResilienceTests.cs::Update_WhileCloudinaryIsSlow_ShouldInvalidateCacheBeforeDeletingOldImage` | NFR-07 |
| TC-33 | T | `Integration/CacheInvalidationTests.cs::GetAll_HitAfterFirstCall_ThenMissWithNewPostFirstAfterCreate` | FR-15, FR-16 |
| TC-34 | T | `Controllers/PostsControllerCacheAsideTests.cs::GetAll_WhenVersionKeyMissing_ShouldReadVersionZeroKey` | FR-15 |
| TC-35 | T | `Controllers/PostsControllerCacheAsideTests.cs::GetAll_WhenCachedPageSizeDiffers_ShouldFallThroughToMongo` | FR-15 |
| TC-36 | T | `Integration/ViewCounterFlowTests.cs::IncrementView_FirstViewOfPostWithMongoViews_ShouldContinueFromMongoValue` | FR-17 |
| TC-37 | T | `Integration/ViewCounterFlowTests.cs::IncrementView_FiftyParallelViews_ShouldCountEveryOne` | FR-17 |
| TC-38 | T | `Integration/ViewCounterFlowTests.cs::IncrementView_UnknownId_ShouldReturn404AndNotCreateCounter` | FR-17 |
| TC-39 | T | `Integration/ViewCounterFlowTests.cs::Flush_ShouldWriteRedisCounterToMongoAndEmptyDirtySet` | FR-18 |
| TC-40 | T | `Integration/ResilienceTests.cs::Flush_WhenMongoWriteFails_ShouldKeepPostIdDirtyForNextRound` | FR-18, NFR-07 |
| TC-41 | T | `Integration/ViewCounterFlowTests.cs::CacheStats_AfterOneMissAndOneHit_ShouldCountEachOnce` | FR-19 |
| TC-42 | T | `Integration/HealthEndpointTests.cs::Health_WithMongoAndRedisUp_ShouldReportHealthyForBoth` | FR-20 |
| TC-43 | T | `Integration/ResilienceTests.cs::RedisDown_PublicReadsServeFromMongo_SessionActionsReturn503_HealthUnhealthy` | NFR-05, FR-20 |
| TC-44 | T | `Services/CloudinaryImageStorageServiceTests.cs::Constructor_ShouldCapHttpTimeoutAt15Seconds` | FR-21 |
| TC-45 | T | `src/frontend/src/components/CacheStatusBadge.test.jsx` (tên test lấy khi viết) | IR-02 |
| TC-46 | A | `scripts/Benchmark/results/2026-10-25-chinh-thuc/summary.json` | NFR-01…NFR-04 |
| TC-47 | T | `scripts/SeedRedis/test_seed_redis.py` + `scripts/SeedRedis/verify_seed_redis.py` | DR-03 |
| TC-48 | T | `scripts/SeedPosts/verify_real.py` (+ `test_seed.py`) | DR-03 |
| TC-49…51 | D | Phụ lục D bước 1, 2, 3 | NFR-01, NFR-02, FR-14, FR-05, NFR-09 |
| TC-52 | I | `docs/bao-cao-nguyen-ly-cache-aside.md` | NFR-09 |
| TC-53 | I | `docs/redis-keyspace.md`, `docs/mongodb-schema.md` | DR-01, DR-02 |
| TC-54 | I | `scripts/DocCheck/check_srs.py` | NFR-08 |
| TC-55 | I | `AGENTS.md` §4 + Phụ lục C.2 cột phụ trách | NFR-09 |

Danh mục thật phải tách TC-49, TC-50, TC-51 thành ba dòng — C12 đọc từng dòng `| TC-NN |`.

IR-01, IR-03…IR-05 lấy test Vitest tương ứng trong `src/frontend/src/pages/*.test.jsx` khi viết.

## Danh sách sửa (đánh dấu khi xong)

- [ ] D1 cookie `SessionId` (7 chỗ) · [ ] D2 GUID dạng `D` · [ ] D3 username ≤ 50, password 6–72
- [ ] D4 field stats · [ ] D5 `POST /api/images`, REST + SHA1 · [ ] D6 RedisInsight 5540
- [ ] D7 `redis:7-alpine` · [ ] D8 Driver 3.11 / SE.Redis 3.1 · [ ] D9 React 19 / Vite 8 / Tailwind 4
- [ ] D10 12 bài/trang (frontend), API mặc định 10 · [ ] D11 badge chỉ ở trang chi tiết · [ ] D12 `CacheStatusBadge.jsx`
- [ ] D13 hậu tố `-2, -3`, 409 · [ ] D14 `LockReleaseAsync` (lệnh cụ thể chờ Phase 4) · [ ] D15 37 ticket, trạng thái thật
- [ ] D16 5 đợt · [ ] D17 câu NFR-02 · [ ] D18 số đo thật trong demo · [ ] D19 `volatile-lru` chỉ ở deploy
- [ ] D20 bỏ HTTP/2 · [ ] D21 bỏ "< 1 ms" · [ ] D22 bỏ "Clean Architecture" · [ ] D23 yêu cầu ≥ 100 bài
- [ ] D24 không chia điểm con phần 2, 3 · [ ] Thêm: `/me`, chuyên mục, `/api/health`, `AdminOnly`, `all` + `pageSize`, 400/404 khi thu hồi, 503, deploy, net10.0

## Related Code Files

- Modify: `docs/SRS.md` (viết lại toàn bộ thành v3.0)
- Read only: mọi file trong Context Links

## Tests Before

Kết quả đỏ của Phase 2 (`reports/02-ket-qua-do-tren-v2.txt`) là test trước. Không viết thêm.

## Refactor

Viết lại theo dàn ý, từng phần một, chạy checker sau mỗi phần với `--only` tương ứng:

| Phần | Lệnh kiểm nhanh |
|---|---|
| 1.6 bảng DB | `--only C11` |
| 3.1, 3.2 | `--only C1,C2,C4,C6` |
| 3.4, Phụ lục A, B | `--only C5,C9` |
| 2.1, Phụ lục D | `--only C3,C7,C8` |
| Phụ lục C, E | `--only C10,C12` |

## Implementation Steps

1. Viết phần "Thông tin tài liệu" và "Lịch sử phiên bản" trước (liệt kê D1–D24).
2. Viết lần lượt theo dàn ý. Nội dung đã đúng ở v2.0 (giải thích Cache-Aside, versioning, write-behind,
   3 sơ đồ mermaid) thì giữ, chỉ sửa chi tiết sai.
3. Phần nào đã có tài liệu chuẩn (`docs/redis-keyspace.md`, `docs/mongodb-schema.md`) thì tóm tắt và dẫn link,
   không chép nguyên văn để khỏi lệch về sau.
4. Mỗi phần xong chạy `--only` tương ứng. Cuối cùng chạy đủ 12 phép kiểm.
5. Đọc lại toàn văn một lượt: câu chữ, dấu tiếng Việt, sơ đồ mermaid hiển thị được (xem trên GitHub/VS Code preview).

## Todo

- [x] Lịch sử phiên bản
- [x] Phần 1 (có bảng DB-01…DB-19)
- [x] Phần 2
- [x] Phần 3 (FR-01…FR-22, IR, NFR, DR)
- [x] Phụ lục A–G
- [x] Checker thoát 0
- [x] Đọc lại toàn văn + xem preview mermaid

## Tests After

```bash
cd /Users/quan/HUIT_CNTT/NoSQL/NoSQL-NewsCacheSession
python3 scripts/DocCheck/check_srs.py; echo "exit=$?"         # mong đợi exit=0
python3 -m unittest discover -s scripts/DocCheck -p 'test_*.py' -v
```

## Test Scenario Matrix

| Mức | Kịch bản | Cách kiểm |
|---|---|---|
| Critical | Còn sót sai lệch nội dung (cookie, cổng, stats, endpoint) | C1, C4, C6, C7 |
| Critical | Yêu cầu không có tiêu chí chấp nhận hoặc không có TC | C12 |
| High | Số đo trong SRS khác `summary.json` | C9 |
| High | Ticket CSV ghi sai trạng thái | C10 |
| Medium | Đường dẫn file trong ma trận Jira sai | C3 |
| Medium | Mermaid lỗi cú pháp | Xem preview (thủ công) |

## Success Criteria

- `check_srs.py` thoát `0`; unit test xanh.
- Danh sách sửa D1–D24 + phần bổ sung đều được đánh dấu.

## Risk Assessment

- Checker xanh nhưng câu chữ vẫn sai ý (checker không hiểu nghĩa) → bước 5 đọc lại toàn văn; Phase 4 đối chiếu sống.
- Viết lại làm mất nội dung đúng của v2.0 → so `diff reports/srs-v2.0.md docs/SRS.md` trước khi kết thúc phase.

## Security Considerations

- Không ghi URL deploy kèm chuỗi kết nối, không ghi mật khẩu tài khoản demo vào SRS.

## Regression Gate

Hai lệnh ở Tests After.

## Next Steps

Phase 4 kiểm chứng trên stack thật những điều checker không đo được (header, cookie, lệnh Redis thật, số bài).
