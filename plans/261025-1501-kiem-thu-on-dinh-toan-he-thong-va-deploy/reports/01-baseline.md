# Phase 1 — Môi trường QA và baseline (26/10/2026)

Mã kiểm thử: nhánh `develop`, commit `9665335`.

## Stack QA (tách khỏi demo)

| Thành phần | Tên / cổng | Ghi chú |
|---|---|---|
| MongoDB | container `news-mongo-qa`, `27019→27017`, `mongo:7.0` | DB `newsdb_qa` |
| Redis | container `news-redis-qa`, `6380→6379`, `redis:7-alpine` | `--save "" --appendonly no` (restart là mất sạch key) |
| API | `dotnet NewsCacheSession.Api.dll --urls http://localhost:5135` | Build từ `develop` ra thư mục riêng trong scratchpad, biến môi trường trong `qa.env` (không commit) |
| Vite | `npx vite --config vite.qa.config.mjs` → `:3001` | File config trong scratchpad import `src/frontend/vite.config.js`, chỉ đổi cổng + proxy `/api → :5135` |

Spike Vite (bước 5) **thành công** — không cần phương án dự phòng dừng PID 59923.

## Baseline (cổng hồi quy cho các phase sau)

| Lệnh | Kết quả |
|---|---|
| `dotnet test` | 27/27 pass (142 ms) |
| `npx vitest run` | 11 file, 103/103 pass |
| `npx oxlint` | exit 0, không cảnh báo |
| `npm run build` | build OK (JS 365 kB / gzip 110.9 kB) |
| `pytest` SeedPosts (venv) | 17 pass, 11 subtest pass |
| `pytest` SeedRedis (venv, bỏ `test_integration.py`) | 33/33 pass |
| `pytest` Benchmark (venv) | 14/14 pass |

## Kết luận G5 — test SeedRedis fail: **lỗi môi trường, không phải lỗi code**

- Python hệ thống (3.15, không venv): `python3 -m unittest discover` → `FAILED (failures=1, errors=1)`,
  đúng 2 test như G5 ghi.
- Cùng lệnh trong venv có đủ `requirements.txt` → `Ran 37 tests ... OK (skipped=4)`.
- Tái hiện tay `verify.main()` trên Python hệ thống in ra:
  `{"ok": false, "errorType": "ModuleNotFoundError", ...}` — Python hệ thống thiếu `pymongo`/`bson`/`redis`
  (`ModuleNotFoundError: No module named 'bson'`), verifier bắt lỗi import và trả mã 1.
- → Mục D1 ở Phase 5 **không cần sửa**. Chỉ cần nhắc trong hướng dẫn: chạy test script trong venv đã cài `requirements.txt`.

## Seed 100 bài vào `newsdb_qa` (đồng thời là test `seed.py`)

```
seed.py --dry-run   → Dry run thành công: tạo 100 bài mẫu; không ghi MongoDB.
seed.py             → Đã seed 100 bài ... (100 mới, 0 đã tồn tại). Chuyên mục được dùng: 5
seed.py (lần 2)     → (0 mới, 100 đã tồn tại)        ← không nhân đôi
seed.py --count 50  → SCRUM-32 yêu cầu tối thiểu 100 bài; --count phải >= 100.
```
Kiểm tra bằng mongosh: `{"n":100,"withImg":100,"catOid":100,"pascal":0,"cats":5}`, field của một
document: `_id, slug, authorId, categoryId, content, createdAt, deletedAt, imageUrl, isDeleted, title, updatedAt, views`.

## Smoke tay (bước 6)

Trực tiếp API `:5135`:
```
health: Healthy
totalItems: 100
GET#1 X-Cache: MISS
GET#2 X-Cache: HIT
post:{id} type=string ttl=600
register qa_admin: {... "role":"admin"} 201      ← user đầu tiên là admin
register qa_user:  {... "role":"user"}  201
cookie: #HttpOnly_localhost SessionId
HGETALL session: userId … username qa_admin role admin loginAt 1792951514 lastActive 1792951514
TTL session: 1800
me: {... "expiresInSeconds":1799}
```
Qua Vite `:3001`: `totalItems: 100`, `x-cache: MISS` → `HIT`, đăng nhập `qa_user` rồi `/api/auth/me` 200.

## Không đụng dữ liệu demo

- `newsdb` trong `news-mongo` (27018): vẫn 10 150 bài chưa xóa.
- Redis demo (`news-redis`, 6379): `DBSIZE = 0` (G3 ghi 1 key tối 25/10 — key đó đã tự hết TTL, không do QA).
- API demo PID 59923 (`:5134`) và Vite PID 55807 (`:3000`) không bị dừng.

## Ghi chú phụ

- Script smoke đầu tiên viết bằng bash lỗi `400` ở đăng ký: bash 3.2 của macOS parse sai dấu nháy kép lồng
  trong `"$(curl -d "{\"…\"}")"`. Lỗi của script kiểm thử, không phải API (gọi tay cùng body → 201).
  Phase 6 viết smoke bằng Python để tránh.
