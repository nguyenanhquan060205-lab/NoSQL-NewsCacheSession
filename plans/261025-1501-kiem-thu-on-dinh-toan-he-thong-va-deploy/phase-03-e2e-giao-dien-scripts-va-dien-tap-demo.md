---
phase: 3
title: "E2E giao diện, script SV3 và diễn tập demo"
status: pending
priority: P1
effort: "4h"
dependencies: [1, 2]
---

# Phase 3: E2E giao diện, script SV3 và diễn tập demo

## Goal
Chứng minh mọi màn hình và script của nhóm chạy đúng trên trình duyệt thật, rồi diễn tập trơn
3 bước demo theo đề trên stack demo chạy **mã mới nhất** của nhánh `develop`.

## Scout pass trước khi làm
- Đọc `src/frontend/src/pages/*.jsx`, `docs/phan-cong-va-kich-ban-demo.md` mục 6 và 10.
- Kiểm tra skill trình duyệt đã cài (ưu tiên `ak-agent-browser`) trước khi dùng.

## Key Insights
- G20: chế độ dev hiện bài mẫu giả khi API lỗi — phải kiểm tra banner `isPreview` có đủ rõ không.
- G4: `seed_redis.py` chỉ chạy với `localhost:27017` → seed Redis demo **sau** khi trả cổng 27017
  cho container (bạn đã đồng ý nhường cổng).
- Session seed có TTL tối đa 30 phút → seed Redis **ngay trước** buổi demo, không seed sớm.

## Phần A — E2E trên stack QA (Vite `:3001` → API `:5135`)

| Mức | Người | Kịch bản trên trình duyệt | Kỳ vọng |
|---|---|---|---|
| Critical | Định | Trang chủ: danh sách, phân trang, lọc chuyên mục | Đúng số bài, URL có `categoryId`, không lỗi console |
| Critical | Định+Quân | Mở chi tiết 2 lần | Badge MISS rồi HIT kèm thời gian; tab Network thấy `X-Cache` |
| High | Quân | Lượt xem trên trang chi tiết | Tăng 1 mỗi lần mở bài khác/mở lại |
| Critical | Định | Đăng ký, đăng nhập, sai mật khẩu, đăng xuất | Thông báo lỗi đúng; Navbar đổi trạng thái |
| Critical | Như | Admin tạo bài (có chuyên mục) → sửa → xóa | Bài lên đầu trang chủ; sửa xong mở lại thấy tiêu đề mới (MISS); xóa xong trang chi tiết báo không tồn tại |
| High | Như | User thường mở `/posts/{id-bài-seed}/edit` và lưu | Thông báo 403 dễ hiểu, bài không đổi |
| High | Định | `/admin/posts`, `/admin/sessions` với user thường | Bị chặn bởi `RequireAdmin` |
| High | Định+Quân | Trang quản lý phiên: TTL đếm lùi, thu hồi phiên tab khác | Tab bị thu hồi gọi API tiếp theo → về trang đăng nhập |
| Medium | Định | Upload ảnh khi chưa cấu hình Cloudinary | Thông báo 503 rõ ràng, form không vỡ |
| Medium | Định | F5 trực tiếp ở `/posts/{id}` và `/admin/posts` | Trang hiện đúng (Vite đã fallback) |
| Medium | Định | Dừng API `:5135`, tải lại trang chủ (G20) | Ghi lại: có banner "dữ liệu mẫu" đủ rõ hay trông như hệ thống bình thường |
| Medium | Định | Khung 375px (điện thoại) | Không tràn ngang, nút bấm được |

## Phần B — Script của SV3 (venv từ Phase 1)
1. `seed.py`: chạy lại lần 2 trên `newsdb_qa` → không nhân đôi; `--count 50` bị chặn (định mức ≥100).
2. Test Python: SeedPosts, SeedRedis (kết luận G5), Benchmark — chạy bằng `pytest` trong venv.
3. `benchmark.py` bản ngắn trỏ vào stack QA:
   `python scripts/Benchmark/benchmark.py --api http://localhost:5135 --redis redis://localhost:6380/0 --posts 5 --rounds 2 --stampede-trials 1 --load-levels 1,10 --load-requests 100 --label qa-kiem-thu`
   → sinh đủ file trong `results/qa-kiem-thu/`; `plot.py` vẽ được biểu đồ. Không ghi đè
   `results/2026-10-25-chinh-thuc/`; xóa `results/qa-kiem-thu/` sau khi kiểm (không commit).

## Phần C — Chuẩn bị stack demo và diễn tập
1. Sao lưu trước khi đụng: `docker exec news-mongo mongodump --db newsdb --archive=/tmp/newsdb.archive`
   rồi `docker cp` ra scratchpad.
2. Trả cổng 27017: `brew services stop mongodb-community`, rồi `docker compose up -d --force-recreate mongo`
   (volume `nosql-newscachesession_mongo_data` giữ nguyên dữ liệu). Kiểm tra `docker compose ps` thấy `27017->27017`
   và `totalItems` vẫn 10 150.
3. Hỏi trước khi dừng API cũ PID 59923 (chạy từ 23/10), rồi chạy lại API từ `develop` ở `:5134`
   **không cần** biến môi trường Mongo nữa — chứng minh README chạy đúng như viết.
4. Seed Redis demo ngay trước diễn tập: `seed_redis.py --demo-username <tài-khoản-role-user> --dry-run`
   rồi chạy thật; `verify_seed_redis.py`; `redis-cli DBSIZE` trong khoảng 20–50, TTL khác nhau.
5. Diễn tập 3 bước theo đề, **2 lượt liên tiếp**, bấm giờ từng bước:
   - Bước 1 (Định): F12 → bài chưa mở lần 1 (MISS, đọc MongoDB) vs lần 2 (HIT, đọc Redis).
   - Bước 2 (Như sửa, Quân chứng minh): sửa bài → RedisInsight thấy `post:{id}` biến mất ngay, `posts:ver` tăng.
   - Bước 3 (Định): RedisInsight mở `session:{id}` thấy TTL đếm lùi; thao tác 1 lần thấy TTL về 1800.
6. Ghi `reports/03-e2e-va-dien-tap.md`: ảnh chụp/ghi chú từng kịch bản, thời gian từng bước, lỗi gặp.
   Quay video dự phòng là SCRUM-45 của Định — báo Định dùng lượt diễn tập thứ hai để quay.

## Tests Before / After
- Before: Phase 2 regression gate xanh trên `develop`; `npx vitest run` + `npx oxlint` xanh.
- After: mọi dòng Critical ở Phần A pass; 2 lượt demo liên tiếp không lỗi; Redis demo 20–50 key.

## Refactor
Không sửa code ở phase này. Lỗi tìm thấy ghi vào báo cáo, sửa ở Phase 5.

## Dependency map
- Cần Phase 1 (Vite QA, venv) và Phase 2 (API đã được kiểm chứng ở tầng HTTP).
- Lỗi giao diện → Phase 5 (sửa trong file của Định sau khi Định đồng ý).

## Success Criteria
- Báo cáo `reports/03-e2e-va-dien-tap.md` có kết quả cho từng dòng bảng Phần A và Phần B.
- `README.md` chạy đúng như viết trên máy này (không cần biến môi trường ẩn).

## Risk Assessment
- `force-recreate` nhầm volume → đã sao lưu ở bước C1, kiểm `totalItems` ngay sau khi tạo lại.
- Dừng Mongo Homebrew ảnh hưởng project `qlsinhvien_db` → bật lại bằng `brew services start mongodb-community` khi cần (container phải nhường 27017 trước).
- Vite `:3000` (PID 55807) của bạn chạy cùng working tree → tự nhận code mới, không cần khởi động lại.

## Security Considerations
Tài khoản demo và mật khẩu chỉ ghi trong scratchpad, không ghi vào báo cáo commit lên repo.

## Todo
- [x] E2E Phần A trên stack QA (12 kịch bản)
- [x] Script SV3 Phần B: seed chạy lại, test Python, benchmark QA, plot
- [x] Sao lưu `newsdb`, trả cổng 27017, tạo lại container theo compose
- [x] Hỏi rồi khởi động lại API demo `:5134` từ `develop`
- [x] Seed Redis demo 20–50 key ngay trước diễn tập
- [x] Diễn tập 3 bước × 2 lượt, ghi `reports/03-e2e-va-dien-tap.md`
