# Frontend NewsCacheSession

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

## SCRUM-38 — Badge cache trang chi tiết

Trang `/posts/{id}` hiện `CACHE HIT`, `CACHE MISS` hoặc `CACHE UNKNOWN` theo header
`X-Cache` của GET `/api/posts/{id}`. `postsApi.getById` giữ nguyên các field Axios
response, thêm `cacheInfo: { status, durationMs }`; form sửa bài vẫn đọc `response.data`.

Thời gian đo riêng GET tại trình duyệt, gồm network/proxy/API và xử lý response Axios.
Không gồm POST `/view`, tải ảnh hay render; không phải thời gian riêng Redis và có thể
khác Duration trong F12. Không suy luận trạng thái từ tốc độ hoặc cam kết HIT luôn <5ms.
Header thiếu/lạ → UNKNOWN; clock lỗi → chưa đo được thời gian; lỗi GET giữ màn hình lỗi.

### Kiểm tra và demo

Từ thư mục `src/frontend`:

```powershell
npm test
npm run lint
npm run build
npm run dev
```

1. Chạy MongoDB, Redis và API tại `http://localhost:5134`. Vite proxy `/api` sang API.
2. Chọn bài thật chưa có cache `post:{id}` bằng kiểm tra read-only, hoặc đợi TTL tự hết.
   Không GET chi tiết trước để kiểm tra vì sẽ warm cache; không FLUSHDB/xóa key hay sửa bài thật để ép MISS.
3. Mở trang chi tiết và F12 Network (Disable cache HTTP), chọn đúng GET `/api/posts/{id}`.
   Đối chiếu header `X-Cache: MISS` với badge, rồi F5 cùng bài để thấy HIT.
4. POST `/view` là request riêng; mỗi lần mở trang vẫn tăng lượt xem theo chức năng hiện có.

Badge không xuất hiện ở trang danh sách/admin. Giữ proxy same-origin; deployment khác
origin cần nhóm phối hợp allowed origin, credentials và expose `X-Cache` ngoài ticket này.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
