---
phase: 4
title: "Kiểm thử trên hệ thống chạy thật và chốt"
status: complete
priority: P1
effort: "3h"
dependencies: [3]
---

# Phase 4: Kiểm thử trên hệ thống chạy thật và chốt

## Goal

Kiểm chứng trên stack thật những điều checker không đo được (header, cookie, lệnh Redis thật gửi đi,
số bài trong CSDL), sửa SRS nếu lệch, gửi báo cáo sai lệch cho chủ sở hữu tài liệu khác, rồi chốt v3.0.

## Context Links

- Lệnh QA có sẵn: `README.md:87-103` (container `news-mongo-qa:27019`, `news-redis-qa:6380`, `NEWS_IT=1`)
- Cách làm QA lần trước: `plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/plan.md` (API QA cổng 5135)
- Ghi chú test: `src/NewsCacheSession.Api/CLAUDE.md` mục "Test" (test nhắm `net10.0`, cần SDK 10)

## Scout trước khi làm (deep mode)

1. `git log --oneline dd9d242..HEAD` — có commit mới đụng `src/` thì chạy lại checker trước.
2. `open -a Docker` (Docker Desktop đang tắt lúc lập plan), chờ `docker info` chạy được.
3. `lsof -nP -iTCP:27017 -iTCP:6379 -iTCP:5540 -iTCP:27019 -iTCP:6380 -iTCP:5135 -sTCP:LISTEN` — cổng nào
   bận bởi tiến trình không phải của mình (ví dụ Mongo Homebrew, xem
   `plans/261025-1501-…/reports/03-e2e-va-dien-tap.md:61`) thì **hỏi Quân**, không tự tắt.
4. Ghi lại trạng thái ban đầu (container nào đang chạy) để cuối phase trả về đúng như cũ.

## Key Insights

- Máy không có `redis-cli` (chỉ có `mongosh`, `curl`) → mọi lệnh Redis chạy qua `docker exec <container> redis-cli`.
- Thao tác **ghi** (đăng ký, đăng nhập, tạo bài, `MONITOR`) chỉ làm trên stack QA. `MONITOR` trên Redis demo
  sẽ in token phiên thật. Stack demo chỉ dùng để **đọc** (đếm bài, đếm key, mở RedisInsight).
- Integration test tự dọn DB `newsdb_it_*` và Redis DB 15 (`src/NewsCacheSession.Api/CLAUDE.md`).
- `LockTakeAsync`/`LockReleaseAsync` là của thư viện. Chưa ai nhìn tận mắt lệnh thật được gửi đi
  (`EX 5` hay `PX 5000`, `DEL` hay `UNLINK`). L10 chốt điều này cho FR-13.

## Tests Before

Chạy toàn bộ bộ test hiện có **trước khi** chạy kiểm tra sống, để biết nền đang xanh:

| # | Lệnh | Mong đợi |
|---|---|---|
| L1 | `dotnet build src/NewsCacheSession.Api/NewsCacheSession.Api.csproj` | Build succeeded |
| L2 | `dotnet test` | Unit xanh, integration `Skipped` |
| L3 | `docker run -d --name news-mongo-qa -p 27019:27017 mongo:7.0` + `docker run -d --name news-redis-qa -p 6380:6379 redis:7-alpine redis-server --save "" --appendonly no` rồi `NEWS_IT=1 dotnet test` | Xanh hết, không `Skipped` |
| L4 | `cd src/frontend && npm test` | Vitest xanh |
| L5 | `for d in Benchmark SeedPosts SeedRedis DocCheck; do python3 -m unittest discover -s scripts/$d -p 'test_*.py'; done` | Xanh. Test cần dịch vụ thật thì ghi rõ bị bỏ qua và lý do |

Đỏ ở bất kỳ dòng nào → dừng, ghi vào report, **không sửa code** (ngoài phạm vi plan). Báo chủ sở hữu file.

## Kiểm tra sống

API QA (chạy nền, ghi PID):

```bash
ASPNETCORE_URLS=http://localhost:5135 \
MongoSettings__ConnectionString="mongodb://localhost:27019/?serverSelectionTimeoutMS=5000" \
MongoSettings__DatabaseName=newsdb_srs_check RedisSettings__ConnectionString=localhost:6380 \
dotnet run --project src/NewsCacheSession.Api
```

| # | Kiểm gì | Lệnh (stack) | Yêu cầu SRS |
|---|---|---|---|
| L6 | Đăng ký tài khoản đầu tiên → `role: admin`; đăng nhập → `Set-Cookie: SessionId=…; max-age=1800; path=/; samesite=lax; httponly` | `curl -si -X POST :5135/api/auth/register` rồi `/login` (QA) | FR-01, FR-02, NFR-06 |
| L7 | `HGETALL session:<id>` đủ 5 field; `TTL` ≤ 1800; gọi `/api/auth/me` xong `TTL` quay về ~1800 | `docker exec news-redis-qa redis-cli` (QA) | FR-02, FR-03, FR-22 |
| L8 | Tạo chuyên mục + bài (admin), `GET /api/posts/<id>` hai lần → `X-Cache: MISS` rồi `HIT`; `TTL post:<id>` ≤ 600; `GET /api/posts/slug/<slug>` không tạo key `post:*` mới | `curl -si` + `docker exec news-redis-qa redis-cli --scan --pattern 'post:*'` (QA) | FR-10, FR-12 |
| L9 | `PUT` bài → `EXISTS post:<id>` = 0, `posts:ver` tăng 1, `GET` kế tiếp `MISS` với tiêu đề mới | QA | FR-07, FR-14, FR-16 |
| L10 | Bật `docker exec news-redis-qa redis-cli MONITOR`, `DEL post:<id>`, gọi `GET` một lần → chép nguyên văn lệnh khóa và lệnh giải phóng | QA | FR-13 (chốt D14, S5) |
| L11 | `POST /api/posts/<id>/view` ×3 → `views` tăng 3; `SMEMBERS posts:dirty_views` có `<id>`; đợi ≥ 60 s → `posts.views` trong Mongo khớp, Set rỗng | QA | FR-17, FR-18 |
| L12 | `GET /api/cache/stats` → đúng 4 key `hits, misses, totalRequests, hitRate` | QA | FR-19 |
| L13 | `docker compose up -d`, `curl -s -o /dev/null -w '%{http_code}' localhost:5540` → `200` | demo (chỉ đọc) | Phụ lục D bước 3 |
| L14 | `mongosh newsdb --quiet --eval` đếm `posts` (tổng, `isDeleted != true`), `categories`, bài có `imageUrl` khác rỗng | demo (chỉ đọc) | DR-03, Phụ lục A |
| L15 | `docker exec news-redis redis-cli --scan --pattern 'session:*' \| wc -l`, `--pattern 'post:*'`, phân bố `TTL` | demo (chỉ đọc) | DR-03 |

### Bản deploy — chỉ GET, không đăng nhập, không POST (Quân chọn 29/10)

API `https://newscachesession-api.onrender.com`, web `https://no-sql-news-cache-session.vercel.app`
(`README.md:5`). Render free ngủ sau 15 phút, lần gọi đầu mất ~1 phút → dùng `curl --max-time 120`.

| # | Kiểm gì | Lệnh | Yêu cầu SRS |
|---|---|---|---|
| L16 | `/health` trả `Healthy` cho cả `mongodb` và `redis` | `curl -s --max-time 120 <API>/health` | FR-20, mục 2.1 môi trường deploy |
| L17 | `GET /api/posts?page=1&pageSize=1` có header `X-Cache`; lấy `id` bài đầu và `totalItems` | `curl -si <API>/api/posts?page=1&pageSize=1` | FR-09, FR-15 |
| L18 | `GET /api/posts/<id>` hai lần → lần 2 `X-Cache: HIT` (lần 1 có thể đã HIT nếu ai vừa đọc — ghi đúng như thấy) | `curl -si` ×2 | FR-12 |
| L19 | `/api/cache/stats` đúng 4 key | `curl -s <API>/api/cache/stats` | FR-19 |
| L20 | Web trả 200; `/api/categories` đếm số chuyên mục | `curl -s -o /dev/null -w '%{http_code}' <WEB>` | IR-01, mục 2.1 |

`totalItems` ở L17 là số bài **trên bản deploy**: lúc deploy là 10.000 bài chưa xóa trên tổng 10.101, 7 chuyên
mục (`plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/reports/06-deploy.md:7`). Máy demo có 10.150 bài
chưa xóa. SRS mục 2.1 và Phụ lục A phải tách rõ hai con số này.
Tổng cộng L16–L20 dưới 20 request: Redis Cloud free giới hạn 100 ops/s, không chạy tải lên bản deploy
(`docs/huong-dan-deploy.md:26`).
Cookie `Secure` trên HTTPS không kiểm ở đây vì cần đăng nhập — đã có
`Integration/AuthFlowTests.cs::Login_BehindHttpsProxy_ShouldMarkSessionCookieSecure`.

L14, L15: nếu CSDL demo trên máy không có đủ dữ liệu (chưa khôi phục), ghi số đo được và nguồn số liệu
trong SRS (báo cáo QA 26/10). **Không** tự chạy khôi phục dữ liệu hay `seed_redis.py` — hỏi Quân trước.

## Related Code Files

- Modify: `docs/SRS.md` (chỉ chỗ lệch với kết quả sống, cập nhật "Lịch sử phiên bản")
- Create: `plans/…/reports/04-kiem-thu-that.md` (lệnh + output rút gọn cho L1–L15)
- Create: `plans/…/reports/04-thong-bao-chu-so-huu.md` (tin nhắn gửi chủ tài liệu, không sửa file của họ)

## Báo cáo cho chủ sở hữu (không tự sửa)

| Tài liệu | Chủ | Lệch |
|---|---|---|
| `AGENTS.md` §6 | cả nhóm (file chung) | Vẫn ghi `SessionAuthMiddleware` là stub và 5 việc SV2 "đang chờ" — đã xong từ 23/10 |
| `docs/checklist-barem.md:22,128` | SV1 | Phần 4 vẫn "chưa có số đo, chưa có biểu đồ" |
| `docs/kich-ban-demo-va-do-hieu-nang.md:368` | SV3 | Còn "Đo ngày __/__/2026 … 101 bài viết" |
| `docs/nosql-jira-tasks.csv` (Jira) | cả nhóm | 11 ticket chưa cập nhật trạng thái; Sprint 1 và Sprint 2 trùng ngày |

## Implementation Steps

1. Scout (mục trên). Ghi trạng thái ban đầu.
2. Chạy L1–L5. Ghi output vào `reports/04-kiem-thu-that.md`.
3. Chạy API QA nền, chạy L6–L12. Rút gọn token phiên trong report (chỉ giữ 8 ký tự đầu).
4. Chạy L13–L15 trên stack demo, chỉ đọc. Chạy L16–L20 trên bản deploy, chỉ GET.
5. Lệch với SRS → sửa SRS, ghi vào "Lịch sử phiên bản", chạy lại checker.
6. Viết `reports/04-thong-bao-chu-so-huu.md`.
7. Dọn: dừng API QA theo PID, `docker rm -f news-mongo-qa news-redis-qa`. Stack demo: trả về trạng thái ở bước 1.
8. Đề xuất commit cho Quân duyệt (không tự commit):
   `docs(srs): đặc tả SRS v3.0 kiểm chứng với code kèm bộ kiểm thử tài liệu` — tiếng Việt, **không** có dòng
   `Co-Authored-By` (`AGENTS.md` §7). Mã ticket: hỏi Quân (SRS không có ticket riêng trong CSV).

## Todo

- [x] Scout + ghi trạng thái ban đầu
- [x] L1–L5 (nền xanh)
- [x] L6–L12 trên QA
- [x] L13–L15 trên demo, chỉ đọc
- [x] L16–L20 trên bản deploy, chỉ GET
- [x] Sửa SRS theo kết quả sống, checker vẫn xanh
- [x] Báo cáo chủ sở hữu
- [x] Dọn tiến trình + container đã bật
- [x] Đề xuất commit, chờ duyệt

## Tests After

```bash
cd /Users/quan/HUIT_CNTT/NoSQL/NoSQL-NewsCacheSession
python3 scripts/DocCheck/check_srs.py; echo "exit=$?"     # exit=0
python3 -m unittest discover -s scripts/DocCheck -p 'test_*.py' -v
docker ps --format '{{.Names}}' | grep -c qa            # 0 — đã dọn container QA
```

## Test Scenario Matrix

| Mức | Kịch bản | Bước |
|---|---|---|
| Critical | Demo bước 1: header `X-Cache` không đổi MISS → HIT | L8 |
| Critical | Demo bước 2: sửa bài mà cache cũ còn | L9 |
| Critical | Demo bước 3: cookie/TTL/RedisInsight sai địa chỉ | L6, L7, L13 |
| High | FR-13 mô tả lệnh khóa khác lệnh thật | L10 |
| High | Số bài trong Phụ lục A khác CSDL | L14 |
| Medium | Worker không flush trong 60 s | L11 |
| Medium | Bản deploy khác máy demo (số bài, eviction) mà SRS gộp làm một | L16–L20 |

## Success Criteria

- L1–L5 xanh (hoặc lỗi được ghi rõ và báo chủ sở hữu).
- L6–L20 khớp SRS v3.0; chỗ nào lệch đã sửa và checker vẫn thoát `0`.
- Không còn container QA hay tiến trình API QA nào chạy sau phase.

## Risk Assessment

- Cổng 27017 bị Mongo Homebrew chiếm → bước scout 3, hỏi trước khi dừng.
- Integration test chậm/treo khi Redis QA chưa sẵn → chờ `docker exec news-redis-qa redis-cli ping` trả `PONG` rồi mới chạy.
- Worker flush mất tới 60 s → L11 đợi đủ, không rút ngắn chu kỳ (không sửa code).
- Render đang ngủ hoặc hết giờ free → L16 timeout. Ghi "không truy cập được lúc <giờ>", không coi là lỗi SRS.

## Security Considerations

- Không `cat`/in `.env.render`, `docs/atlas-credentials.env`. Bản deploy chỉ gọi GET công khai: không đăng ký,
  không đăng nhập, không `POST /view` (đổi bộ đếm thật), không đụng trực tiếp Atlas hay Redis Cloud.
- Mật khẩu tài khoản QA là giá trị dùng một lần, không ghi vào SRS hay commit.
- `MONITOR` chỉ trên Redis QA (`news-redis-qa`, cổng 6380).

## Refactor

Chỉ sửa câu chữ SRS ở chỗ kết quả sống khác mô tả.

## Regression Gate

Ba lệnh ở Tests After + L2 (`dotnet test`).

## Next Steps

Quân duyệt commit. Sau khi commit, gửi `reports/04-thong-bao-chu-so-huu.md` cho Như (SV1), Định (SV3) và nhóm.
