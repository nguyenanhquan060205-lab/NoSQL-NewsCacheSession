---
title: Ẩn nút Viết bài với người không phải admin
date: 2026-10-30
summary: Frontend hiện nút Viết bài cho mọi người dù bản deploy chỉ cho admin đăng bài; chuyển nút vào khối admin và chặn route /posts/new
---

# Ẩn nút Viết bài với người không phải admin

## What happened
Nút "Viết bài" trên thanh điều hướng hiện cho mọi người: khách, user thường và admin.
Bản deploy đặt `PostingSettings:AdminOnly=true`, nên user thường bấm vào, điền hết form
rồi mới nhận lỗi 403 "Bản demo trực tuyến chỉ cho quản trị viên đăng bài và tải ảnh."

Nguyên nhân (đã tái hiện bằng test trước khi sửa):
- `src/frontend/src/components/Navbar.jsx`: link `/posts/new` nằm ngoài khối `user?.role === 'admin'`.
- `src/frontend/src/pages/HomePage.jsx`: khi trang chủ trống, nút "Viết bài đầu tiên" hiện cho mọi người.
- `src/frontend/src/App.jsx`: route `/posts/new` không nằm dưới `RequireAdmin`.

## Decision
- Chuyển link "Viết bài" vào khối chỉ admin thấy, thêm `aria-label="Viết bài"` giống hai link quản trị bên cạnh và bỏ thẻ span `sr-only` bị trùng.
- HomePage: người không phải admin không thấy nút "Viết bài đầu tiên", câu mô tả đổi thành "Bài viết mới sẽ xuất hiện tại đây ngay khi được đăng."
- Đưa `/posts/new` vào nhóm route `RequireAdmin`. Route `/posts/:id/edit` giữ nguyên vì backend vẫn cho tác giả sửa bài của chính mình.
- Không sửa backend. `PostingPolicy` và cờ `AdminOnly` giữ nguyên.

Kiểm tra: test mới trong `Navbar.test.jsx` (admin thấy nút; user và khách không thấy) fail trước khi sửa, pass sau khi sửa. 104/104 test frontend đạt, oxlint sạch, `vite build` thành công.

## Next steps
- `src/frontend/**` thuộc SV3 (Nguyễn Xuân Định). Cần báo SV3 về thay đổi này.
- Chạy local thì `AdminOnly=false`: backend vẫn nhận bài từ user thường qua API, nhưng giao diện không còn đường vào form đăng bài. Nếu muốn user thường được đăng bài khi chạy local, frontend cần biết giá trị cờ, ví dụ thêm `canPost` vào `/api/auth/me` (file của SV1).

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
