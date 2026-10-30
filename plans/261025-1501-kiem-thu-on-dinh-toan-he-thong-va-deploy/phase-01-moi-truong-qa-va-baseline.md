---
phase: 1
title: "Môi trường QA và baseline"
status: pending
priority: P1
effort: "2.5h"
dependencies: []
---

# Phase 1: Môi trường QA và baseline

## Goal
Có một stack QA tách khỏi dữ liệu demo, chạy đúng mã nguồn hiện tại, và một bộ lệnh baseline
mà mọi phase sau dùng làm cổng hồi quy.

## Key Insights
- G1/G2: API đang chạy là bản 23/10 và chỉ đúng DB nhờ biến môi trường; Mongo native chiếm 27017.
- G4: `seed_redis.py` chỉ chạy với `localhost:27017` + `newsdb` → seed Redis chỉ làm được trên
  stack demo sau khi gỡ xung đột cổng (Phase 3), không làm trên QA.
- G21: không sửa `vite.config.js` (file SV3) → dùng file config QA riêng.

## File inventory

| File | Hành động | Ghi chú |
|---|---|---|
| `{scratchpad}/qa.env` | Tạo (không commit) | Biến môi trường cho API QA |
| `{scratchpad}/vite.qa.config.mjs` | Tạo (không commit) | Import config gốc, đổi cổng 3001 + proxy `:5135` |
| Mã nguồn repo | Không đổi | Phase này chỉ dựng môi trường |

## Tests Before (baseline phải ghi lại trước mọi thay đổi)
1. `dotnet test` → kỳ vọng 27/27 (đã thấy tối 25/10).
2. `cd src/frontend && npx vitest run && npx oxlint && npm run build` → 103/103, lint sạch, build OK.
3. Python trong venv riêng: `python3 -m venv {scratchpad}/venv`, cài `requirements.txt` của
   SeedPosts, SeedRedis, Benchmark + `pytest`; chạy test từng thư mục, **bỏ** `test_integration.py`.
   Ghi lại G5 (2 test SeedRedis fail) là lỗi thật hay do môi trường.

## Implementation Steps
1. ~~Chốt mã kiểm thử~~ — **đã xong 25/10**: nhánh `develop` tách từ `main` (`f1dc06a`), commit
   `9665335` chứa bản sửa lượt xem (G13) và bản vá build test (G27). Mọi việc của plan làm trên
   `develop`; chỉ đưa lên `main` ở cuối Phase 5 qua PR. Kiểm tra: `git branch --show-current` = `develop`.
2. Dựng container QA (ghi lại tên + cổng để dọn sau). Redis QA chạy **không lưu xuống đĩa** để
   Phase 4 tái hiện được tình huống mất dữ liệu (image mặc định có RDB, `docker restart` sẽ giữ dữ liệu):
   `docker run -d --name news-mongo-qa -p 27019:27017 mongo:7.0` và
   `docker run -d --name news-redis-qa -p 6380:6379 redis:7-alpine redis-server --save "" --appendonly no`.
3. Nạp 100 bài vào QA bằng script của SV3:
   `MONGODB_URI=mongodb://localhost:27019 MONGODB_DATABASE=newsdb_qa python scripts/SeedPosts/seed.py --dry-run`, rồi chạy thật.
   Đồng thời đây là test của `seed.py`: 100/100 có ảnh, `categoryId` là ObjectId, không có field PascalCase.
4. Chạy API QA từ mã hiện tại ở chế độ nền, theo dõi PID:
   `MongoSettings__ConnectionString=mongodb://localhost:27019 MongoSettings__DatabaseName=newsdb_qa RedisSettings__ConnectionString=localhost:6380 ASPNETCORE_ENVIRONMENT=Development dotnet run --project src/NewsCacheSession.Api --urls http://localhost:5135`.
5. Spike Vite QA: `vite.qa.config.mjs` import `src/frontend/vite.config.js` bằng đường dẫn tuyệt đối,
   đè `server.port=3001` và proxy `/api → http://localhost:5135`; chạy `npx vite --config ...` từ
   `src/frontend`. Nếu spike hỏng: phương án dự phòng là xin phép dừng PID 59923 và chạy API QA ở 5134.
6. Smoke tay trên QA bằng `curl` (cookie jar): `/health` Healthy; `GET /api/posts?pageSize=1`
   `totalItems=100`; `GET /api/posts/{id}` hai lần → `X-Cache: MISS` rồi `HIT`; đăng ký user đầu
   (admin) + user thường; đăng nhập → `redis-cli -p 6380 HGETALL session:{id}` đủ 5 field, `TTL ≈ 1800`.

## Tests After / Regression gate
- Lệnh ở "Tests Before" cho kết quả không tệ hơn baseline.
- Smoke bước 6 pass trên API `:5135` và qua Vite `:3001`.

## Test scenario matrix

| Mức | Kịch bản | Kỳ vọng |
|---|---|---|
| Critical | API QA đọc đúng `newsdb_qa`, không đụng `newsdb` | `totalItems=100`, `newsdb` không đổi số bài |
| Critical | MISS → HIT trên `/api/posts/{id}` | Header `X-Cache` đổi, key `post:{id}` TTL ≤ 600 |
| High | Session Hash sau đăng nhập | Đủ `userId, username, role, loginAt, lastActive`, TTL ≈ 1800 |
| Medium | 2 test SeedRedis fail (G5) | Có kết luận: lỗi code hay phụ thuộc môi trường |

## Success Criteria
- Stack QA chạy, baseline được ghi vào `reports/01-baseline.md` (lệnh + output rút gọn).
- Không tiến trình hay dữ liệu demo nào bị thay đổi.

## Risk Assessment
- Cổng 27019/6380/5135/3001 bận → tìm tiến trình chủ bằng `lsof -i :PORT`, không đổi sang cổng khác.
- Spike Vite hỏng → dùng phương án dự phòng ở bước 5 (phải hỏi trước).

## Security Considerations
- `qa.env` và mật khẩu tài khoản test chỉ nằm trong scratchpad, không commit.

## Rollback / dọn dẹp (khi xong cả plan)
`docker rm -f news-mongo-qa news-redis-qa`; dừng API `:5135` và Vite `:3001` đã khởi động.

## Next Steps
Phase 2 dùng container QA này cho integration test (DB riêng `newsdb_it_*`, Redis DB 15).

## Todo
- [x] Tạo nhánh `develop`, commit bản sửa lượt xem + vá build test (`9665335`)
- [x] Chạy và ghi baseline .NET, Vitest, oxlint, build frontend
- [x] Tạo venv Python, chạy test SeedPosts/SeedRedis/Benchmark, kết luận G5
- [x] Dựng `news-mongo-qa` (27019) và `news-redis-qa` (6380, không lưu đĩa)
- [x] Seed 100 bài vào `newsdb_qa` bằng `seed.py`
- [x] Chạy API QA từ `develop` ở `:5135`
- [x] Spike Vite QA `:3001` (hoặc phương án dự phòng sau khi hỏi)
- [x] Smoke tay trên QA, ghi `reports/01-baseline.md`
