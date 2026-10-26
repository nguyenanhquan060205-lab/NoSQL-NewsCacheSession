---
phase: 4
title: "Độ bền và lỗi biên"
status: pending
priority: P1
effort: "3h"
dependencies: [1, 2]
---

# Phase 4: Độ bền và lỗi biên

## Goal
Biết chính xác hệ thống làm gì khi Redis, MongoDB, Cloudinary hoặc chính API gặp sự cố, khi bị
tải lâu, và khi request chen nhau — để Phase 5 sửa đúng chỗ và để trả lời phản biện bằng số đo.

## Scout pass trước khi làm
- Đọc lại `Services/RedisCacheService.cs`, `Middleware/SessionAuthMiddleware.cs`,
  `Controllers/PostsController.cs` (GetById, Update, Delete) trên `develop`.
- Chỉ thao tác trên container QA `news-redis-qa` / `news-mongo-qa` và API `:5135`. **Không** dừng `news-redis`/`news-mongo` của demo.

## Test scenario matrix

| Mức | Kịch bản | Cách làm | Ghi lại | Giả thuyết |
|---|---|---|---|---|
| Critical | Redis chết khi đang phục vụ | `docker stop news-redis-qa`; gọi danh sách, chi tiết, request có cookie, tạo bài, `/health` | Mã HTTP từng loại; log lỗi | G9 |
| Critical | Redis sống lại | `docker start news-redis-qa` | Bao lâu API tự hồi phục (`AbortOnConnectFail=false`) | G9 |
| High | Redis mất dữ liệu (container QA chạy `--save "" --appendonly no`) | Tăng lượt xem vài bài, chờ worker flush → `docker restart news-redis-qa` (mất sạch key) → xem tiếp → chờ flush | Mongo `views` không bị tụt, đếm tiếp từ số cũ | G13 |
| High | MongoDB chết | `docker stop news-mongo-qa`; gọi bài **đã cache** và bài chưa cache, đăng nhập | HIT vẫn 200? MISS/đăng nhập ra mã gì | — |
| High | API khởi động lại | Dừng và chạy lại API `:5135` | Phiên còn (nằm ở Redis); `/api/cache/stats` về 0 | — |
| High | Lock kẹt | `SET lock:post:{id} x PX 5000` rồi `GET /api/posts/{id}` | Độ trễ thực tế (kỳ vọng ≤ ~5s) và số vòng chờ | G10 |
| High | Cloudinary chậm | Integration test thay `IImageStorageService` bằng bản giả chờ 10s, sửa bài có `imagePublicId` | PUT mất bao lâu; trong lúc chờ `post:{id}` còn tồn tại không | G14 |
| High | Worker flush gặp Mongo lỗi | Đánh dấu dirty, dừng Mongo QA đúng lúc flush, bật lại | ID có còn trong `posts:dirty_views` không | G11 |
| Medium | Tải dài 15 phút | `ab -t 900 -c 20` vào chi tiết + danh sách xen kẽ; mỗi 30s ghi `ps -o rss,%cpu -p <pid>` và `redis-cli -p 6380 INFO clients,memory` | RSS không tăng đều; 0 phản hồi khác 2xx; số kết nối Redis ổn định | — |
| Medium | Dung lượng cache bài dài | `MEMORY USAGE post:{id}` với 5 bài dài nhất (content tới 275 018 ký tự) | Byte/key; ước tính bao nhiêu bài thì đầy Redis Cloud 30 MB | G25 |

## Tests Before
- Phase 2 regression gate xanh.
- Ghi lại số đo "bình thường" (độ trễ trung vị MISS/HIT, RSS lúc nghỉ) để so sánh.

## Implementation Steps
1. Chạy lần lượt từng kịch bản trong bảng, mỗi kịch bản bắt đầu từ trạng thái sạch
   (Redis QA `FLUSHALL` được phép vì là container QA riêng, API khởi động lại nếu cần).
2. Viết thành integration test (thêm vào `tests/.../Integration/`) cho những kịch bản lặp lại được
   trong test: lock kẹt, Cloudinary chậm, Redis mất dữ liệu. Các kịch bản dừng container thì ghi
   thành lệnh trong báo cáo để chạy lại tay sau khi sửa.
3. Ghi `reports/04-do-ben.md`: bảng kết quả, log trích đoạn, kết luận G9/G10/G11/G13/G14/G25.

## Refactor
Không sửa code sản phẩm ở phase này.

## Tests After / Regression gate
- Test mới viết ở bước 2 đang đỏ đúng chỗ có lỗi (làm bằng chứng cho Phase 5) hoặc xanh nếu giả thuyết sai.
- `dotnet test` mặc định vẫn xanh.

## Dependency map
- Kết quả G9 + G10 quyết định thiết kế bản sửa "Redis lỗi thì đọc thẳng MongoDB" ở Phase 5.
- Số đo dung lượng (G25) quyết định cấu hình Redis Cloud ở Phase 6.

## Success Criteria
Mỗi dòng của bảng có kết quả đo được (lệnh + output), không có dòng "chưa thử".

## Risk Assessment
- Lỡ tay dừng container demo → mọi lệnh `docker stop/start/restart` phải có hậu tố `-qa`; kiểm `docker ps` trước mỗi lệnh.
- Tải dài làm máy nóng/chậm khi đang làm việc khác → chạy lúc rảnh, dừng được bằng Ctrl+C.

## Security Considerations
Không có dữ liệu thật trong QA (100 bài seed), không ảnh hưởng tài khoản demo.

## Todo
- [x] Ghi số đo bình thường (độ trễ, RSS)
- [x] Redis chết / sống lại / mất dữ liệu
- [x] MongoDB chết, API khởi động lại
- [x] Lock kẹt, Cloudinary chậm (test), worker gặp Mongo lỗi
- [x] Tải 15 phút + đo dung lượng cache bài dài
- [x] Ghi `reports/04-do-ben.md`
