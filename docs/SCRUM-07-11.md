# Báo Cáo Tóm Tắt Nhiệm Vụ: SCRUM-07 & SCRUM-11
> **Sprint:** Sprint 0  
> **Dự án:** NoSQL - NewsCacheSession (Đề tài 06: Caching bài viết & Session Management)

---

## 1. SCRUM-07: Dựng Docker Compose cho Web App (MongoDB, Redis, RedisInsight)

### Mục tiêu:
Thiết lập hạ tầng CSDL và Cache chạy bằng Docker để toàn bộ thành viên trong nhóm (cả macOS và Windows) có thể khởi động môi trường giống hệt nhau chỉ bằng 1 lệnh duy nhất.

### Những việc đã làm:
1. **Tạo file `docker-compose.yml` gồm 3 dịch vụ:**
   * **`news-mongo`** (`mongo:7.0`): Chạy ở port `27017:27017`, gắn volume `mongo_data` để lưu trữ dữ liệu bền vững.
   * **`news-redis`** (`redis:7-alpine`): Chạy ở port `6379:6379`, bật chế độ ghi AOF (`--appendonly yes`), gắn volume `redis_data`.
   * **`news-redisinsight`** (`redis/redisinsight:latest`): Giao diện web trực quan của Redis, chạy ở port `5540:5540`, phục vụ kịch bản demo quan sát TTL và Key Hashes/Strings.
   * Cấu hình chung mạng bridge: `news-network`.
2. **Cách Chạy**
```bash
# 1. Khởi động DB & Cache: MongoDB (27017), Redis (6379), RedisInsight (5540)
docker compose up -d

# 2. Chạy Backend API (Swagger: http://localhost:5134/swagger)
cd src/NewsCacheSession.Api && dotnet run

# 3. Chạy Frontend (UI: http://localhost:3000)
cd src/frontend && npm run dev
```
3. **Kiểm thử thực tế (100% Pass):**
   * Khởi chạy thành công cả 3 containers (`docker ps`).
   * Ping Redis trả về `PONG`, ghi và đọc thử key thành công.
   * Ping MongoDB engine trả về `{ ok: 1 }`.
   * Gửi HTTP request đến RedisInsight port 5540 trả về `HTTP 200 OK`.

---

## 2. SCRUM-11: Skeleton ASP.NET Core Web API (Config, Kết nối Mongo/Redis, HealthCheck)

### Mục tiêu:
Hoàn thiện khung ứng dụng Backend Web API, cấu hình kết nối an toàn tới MongoDB và Redis, đồng thời xây dựng hệ thống HealthCheck chuẩn mực để giám sát trạng thái kết nối.

### Những việc đã làm:
1. **Cấu hình & Tăng độ bền kết nối (Connection Resilience):**
   * `appsettings.json`: Cấu hình connection string cho Mongo (`localhost:27017`) và Redis (`localhost:6379`).
   * `Program.cs`: Cấu hình Redis với `AbortOnConnectFail = false` giúp backend không bị crash lúc khởi động nếu Redis khởi động trễ 1-2 giây.
   * `MongoContext.cs`: Mở thuộc tính `Database` để hỗ trợ lệnh ping và admin commands.
2. **Đảm bảo tương thích Cross-platform (Windows & macOS):**
   * Giữ chuẩn `<TargetFramework>net8.0</TargetFramework>` (bản LTS phổ biến trên Windows của thành viên trong nhóm).
   * Thêm cờ `<RollForward>Major</RollForward>` để máy nào cài .NET 8, .NET 9 hay .NET 10 đều tự động tương thích và chạy mượt mà.
3. **Xây dựng hệ thống Health Checks:**
   * **`MongoHealthCheck.cs`**: Thực hiện lệnh `ping` MongoDB database, bắt exception và trả về kết quả `Healthy` / `Unhealthy`.
   * **`RedisHealthCheck.cs`**: Gọi `db.PingAsync()` tới Redis server và đo thời gian trễ (latency ms) thực tế.
4. **Cung cấp 2 cổng kiểm tra sức khỏe hệ thống:**
   * **Endpoint REST `/health`**: Trả về cấu trúc JSON chi tiết, phục vụ Docker / Kubernetes / DevOps.
   * **Endpoint Swagger `/api/health`** (`HealthController.cs`): Hiển thị trực quan ngay trên Swagger UI cho giảng viên / tester bấm kiểm tra trực tiếp.

---

## 3. Hướng Dẫn Chạy & Kiểm Thử Nhanh

### Bước 1: Khởi động Database & Cache
```bash
docker compose up -d
```

### Bước 2: Khởi động Backend API
```bash
cd src/NewsCacheSession.Api
dotnet run
```
*API sẽ lắng nghe tại: `http://localhost:5134`*

### Bước 3: Kiểm tra HealthCheck
* **Cách 1 (Swagger UI):** Truy cập `http://localhost:5134/swagger` $\rightarrow$ Chọn mục **Health** $\rightarrow$ `GET /api/Health` $\rightarrow$ Bấm **Try it out** $\rightarrow$ **Execute**.
* **Cách 2 (REST Endpoint):** Truy cập trực tiếp link `http://localhost:5134/health` trên trình duyệt để nhận JSON:
  ```json
  {
    "status": "Healthy",
    "totalDuration": "00:00:00.082",
    "entries": {
      "mongodb": {
        "status": "Healthy",
        "description": "MongoDB connection is healthy."
      },
      "redis": {
        "status": "Healthy",
        "description": "Redis connection is healthy. Latency: 0.73ms"
      }
    }
  }
  ```
* **Cách 3 (Test chịu lỗi):**
  * Tắt Redis: `docker stop news-redis` $\rightarrow$ F5 lại trang `/health` sẽ thấy trạng thái đổi thành `Unhealthy` (Mã 503).
  * Bật lại Redis: `docker start news-redis` $\rightarrow$ F5 lại trang `/health` sẽ lập tức xanh trở lại `Healthy` (Mã 200).
