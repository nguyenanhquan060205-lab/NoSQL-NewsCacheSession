---
phase: 0
title: "TDD Test Infrastructure Setup"
status: completed
priority: P1
effort: "1h"
dependencies: []
ticket: ["SCRUM-35", "SCRUM-37"]
---

# Phase 0: Thiết Lập Hạ Tầng Kiểm Thử TDD (Test Infrastructure Setup)

## 1. Mục Tiêu (Objective)
Để tuân thủ triệt để phương pháp **Test-Driven Development (TDD)** cho toàn bộ các phase tiếp theo:
1. Tạo project test `tests/NewsCacheSession.Tests` bằng .NET 8 xUnit.
2. Cài đặt các thư viện cần thiết: `xunit`, `Moq`, `FluentAssertions`, `Microsoft.AspNetCore.Mvc.Testing`.
3. Thêm project vào file solution `NewsCacheSession.sln`.
4. Tham chiếu `NewsCacheSession.Tests.csproj` tới `src/NewsCacheSession.Api/NewsCacheSession.Api.csproj`.
5. Tạo `TestHelper` hoặc Mock Fixture cho Redis (`IConnectionMultiplexer`, `IDatabase`) và `HttpContext`.

---

## 2. Test Matrix (TDD Enforced)

| Test Case ID | Mục Tiêu | Kết Quả Mong Đợi |
|---|---|---|
| **TC-INFRA-01** | `dotnet test` thực thi trên solution | Solution build thành công, 1 test baseline mẫu pass |
| **TC-INFRA-02** | Tham chiếu API | Project test có thể khởi tạo các class thuộc namespace `NewsCacheSession.Api.Services` |

---

## 3. Các Bước Triển Khai (Implementation Steps)

### Bước 1: Tạo project test
```bash
dotnet new xunit -o tests/NewsCacheSession.Tests
dotnet sln NewsCacheSession.sln add tests/NewsCacheSession.Tests/NewsCacheSession.Tests.csproj
dotnet add tests/NewsCacheSession.Tests/NewsCacheSession.Tests.csproj reference src/NewsCacheSession.Api/NewsCacheSession.Api.csproj
```

### Bước 2: Thêm các packages hỗ trợ kiểm thử
```bash
dotnet add tests/NewsCacheSession.Tests package Moq
dotnet add tests/NewsCacheSession.Tests package FluentAssertions
dotnet add tests/NewsCacheSession.Tests package Microsoft.AspNetCore.Mvc.Testing
```

### Bước 3: Tạo `TestDoubles/RedisDatabaseMock.cs`
Mock `IDatabase` và `IConnectionMultiplexer` để có thể chạy unit test độc lập không phụ thuộc vào Redis container khi chạy CI/CD hoặc test nhanh.

---

## 4. Lệnh Kiểm Tra & Nghiệm Thu (Verification Commands)

```bash
dotnet build
dotnet test
```
