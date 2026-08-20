# 📐 Quy Chế Tổ Chức Repo — Nhóm 3 Thành Viên

## 1. Chiến lược nhánh (Branching Strategy)

Nhóm dùng mô hình **Git Flow đơn giản** — mỗi SV tạo **nhiều feature branch nhỏ**, mỗi branch = 1 chức năng cụ thể:

```
main                          ← Code ổn định, chỉ merge từ dev
  │
  └── dev                     ← Nhánh tích hợp, test tổng hợp ở đây
        │
        │── SV1 (Data Architect & CRUD Lead)
        │   ├── feature/sv1-auth-register-login
        │   ├── feature/sv1-auth-logout-me
        │   ├── feature/sv1-posts-getall-create
        │   └── feature/sv1-posts-delete
        │
        │── SV2 (Advanced Query Specialist)
        │   ├── feature/sv2-session-middleware
        │   ├── feature/sv2-cache-aside-getbyid
        │   ├── feature/sv2-cache-invalidation-update
        │   └── feature/sv2-incr-viewcount
        │
        └── SV3 (Fullstack Integrator & DB Tester)
            ├── feature/sv3-seed-100-posts
            ├── feature/sv3-frontend-homepage
            ├── feature/sv3-frontend-login-page
            ├── feature/sv3-frontend-post-detail
            └── feature/sv3-benchmark
```

### Tại sao tách nhỏ?

- **Dễ review** — mỗi PR chỉ thay đổi 1-2 file, không bị loạn
- **Ít conflict** — branch nhỏ sống ngắn, merge nhanh, giảm xung đột
- **Dễ rollback** — nếu feature lỗi, chỉ revert 1 PR nhỏ, không mất hết
- **Thể hiện tiến độ** — giáo viên thấy commit history rõ ràng ai làm gì

### Bảng chi tiết

#### SV1 — Data Architect & CRUD Lead

| Branch | Chức năng | File chính sửa |
|---|---|---|
| `feature/sv1-auth-register-login` | Đăng ký + Đăng nhập (hash password, tạo Session Redis) | `AuthController.cs` |
| `feature/sv1-auth-logout-me` | Đăng xuất + Lấy thông tin session | `AuthController.cs` |
| `feature/sv1-posts-getall-create` | Danh sách bài viết (phân trang) + Tạo bài mới | `PostsController.cs` |
| `feature/sv1-posts-delete` | Xóa bài viết + xóa cache liên quan | `PostsController.cs` |

#### SV2 — Advanced Query Specialist

| Branch | Chức năng | File chính sửa |
|---|---|---|
| `feature/sv2-session-middleware` | Đọc Cookie → Redis HGETALL → gán HttpContext | `SessionAuthMiddleware.cs` |
| `feature/sv2-cache-aside-getbyid` | Cache-Aside: GET Redis → miss → MongoDB → SET + TTL | `PostsController.cs` |
| `feature/sv2-cache-invalidation-update` | Sửa bài viết + DEL cache cũ (Invalidation) | `PostsController.cs` |
| `feature/sv2-incr-viewcount` | INCR bộ đếm lượt xem real-time | `PostsController.cs` |

#### SV3 — Fullstack Integrator & DB Tester

| Branch | Chức năng | File chính sửa |
|---|---|---|
| `feature/sv3-seed-100-posts` | Nạp 100 bài viết vào MongoDB (Faker) | `scripts/SeedPosts/seed.py` |
| `feature/sv3-frontend-homepage` | Trang chủ: danh sách bài viết + Navbar | `HomePage.jsx`, `Navbar.jsx`, `PostCard.jsx` |
| `feature/sv3-frontend-login-page` | Trang đăng nhập / đăng ký | `LoginPage.jsx` |
| `feature/sv3-frontend-post-detail` | Chi tiết bài viết + đo response time + tạo/sửa bài | `PostDetailPage.jsx`, `CreateEditPostPage.jsx` |
| `feature/sv3-benchmark` | Benchmark DB vs Cache + vẽ biểu đồ | `scripts/Benchmark/benchmark.py` |

### Nguyên tắc

| Nhánh | Ai push | Khi nào merge | Cách merge |
|---|---|---|---|
| `main` | Không ai push trực tiếp | Khi `dev` đã test ổn định, sẵn sàng demo | Pull Request từ `dev` → `main` |
| `dev` | Không ai push trực tiếp | Khi feature branch hoàn thành | Pull Request từ `feature/*` → `dev` |
| `feature/sv1-*` | Chỉ SV1 | Khi hoàn thành + test | Tạo PR vào `dev`, nhờ 1 SV khác review |
| `feature/sv2-*` | Chỉ SV2 | Khi hoàn thành + test | Tạo PR vào `dev`, nhờ 1 SV khác review |
| `feature/sv3-*` | Chỉ SV3 | Khi hoàn thành + test | Tạo PR vào `dev`, nhờ 1 SV khác review |

---

## 2. Cách thiết lập ban đầu

### Bước 1: Tạo nhánh `dev` và đẩy lên remote

```bash
# Người quản lý repo (leader) thực hiện:
git checkout main
git pull origin main
git checkout -b dev
git push -u origin dev
```

### Bước 2: Mỗi thành viên tạo nhánh feature từ `dev`

**SV1:**
```bash
git checkout dev
git pull origin dev
git checkout -b feature/sv1-auth-crud
git push -u origin feature/sv1-auth-crud
```

**SV2:**
```bash
git checkout dev
git pull origin dev
git checkout -b feature/sv2-cache-session
git push -u origin feature/sv2-cache-session
```

**SV3:**
```bash
git checkout dev
git pull origin dev
git checkout -b feature/sv3-frontend-scripts
git push -u origin feature/sv3-frontend-scripts
```

### Bước 3: (Tuỳ chọn) Bảo vệ nhánh `main` trên GitHub

1. Vào **Settings** → **Branches** → **Add branch protection rule**
2. Branch name pattern: `main`
3. Tick:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (1 người)
4. Save changes

---

## 3. Quy trình làm việc hàng ngày

### 3.1 Trước khi code — Luôn pull mới nhất

```bash
# Đảm bảo đang ở nhánh của mình
git checkout feature/sv1-auth-crud   # (hoặc sv2, sv3)

# Lấy code mới nhất từ dev
git pull origin dev
```

### 3.2 Trong khi code — Commit thường xuyên

```bash
# Xem những gì đã thay đổi
git status

# Stage file cụ thể (KHUYẾN KHÍCH — rõ ràng hơn)
git add src/NewsCacheSession.Api/Controllers/AuthController.cs

# Hoặc stage tất cả
git add -A

# Commit với message có ý nghĩa
git commit -m "feat(auth): implement Register endpoint"
```

### 3.3 Sau khi code — Push lên remote

```bash
git push origin feature/sv1-auth-crud
```

### 3.4 Khi hoàn thành — Tạo Pull Request

1. Vào GitHub → **Pull Requests** → **New Pull Request**
2. Base: `dev` ← Compare: `feature/sv1-auth-crud`
3. Viết tiêu đề + mô tả ngắn
4. Gán reviewer (thành viên khác)
5. Chờ review → Merge

---

## 4. Quy ước đặt tên commit (Commit Convention)

Dùng format: **`<type>(<scope>): <mô tả ngắn>`**

### Các type phổ biến

| Type | Dùng khi | Ví dụ |
|---|---|---|
| `feat` | Thêm chức năng mới | `feat(auth): implement Login endpoint` |
| `fix` | Sửa lỗi | `fix(cache): fix null reference khi cache miss` |
| `docs` | Cập nhật tài liệu | `docs: cập nhật hướng dẫn seed data` |
| `style` | Sửa format, CSS | `style(frontend): chỉnh layout PostCard` |
| `refactor` | Tái cấu trúc code | `refactor(posts): tách PostService riêng` |
| `test` | Thêm test | `test(benchmark): thêm benchmark 50 bài viết` |
| `chore` | Cập nhật config, package | `chore: thêm package BCrypt.Net-Next` |

### Các scope theo thành viên

| Thành viên | Scope thường dùng |
|---|---|
| SV1 | `auth`, `posts`, `models`, `db` |
| SV2 | `cache`, `session`, `middleware`, `redis` |
| SV3 | `frontend`, `seed`, `benchmark`, `ui` |

### Ví dụ commit history tốt

```
feat(auth): implement Register endpoint với BCrypt
feat(auth): implement Login endpoint + set Cookie SessionId
feat(posts): implement GetAll với phân trang Skip/Limit
feat(cache): implement Cache-Aside cho GetById
feat(cache): implement Cache Invalidation cho Update + Delete
feat(session): implement SessionAuthMiddleware
feat(frontend): implement HomePage gọi API danh sách bài viết
feat(seed): nạp 100 bài viết mẫu bằng Faker
fix(cache): sửa lỗi deserialize PostResponse thiếu field
docs: cập nhật README hướng dẫn chạy project
```

---

## 5. Quy tắc tránh xung đột (Conflict)

### 5.1 File nào ai sửa?

| File / Thư mục | SV1 | SV2 | SV3 | Ghi chú |
|---|---|---|---|---|
| `Controllers/AuthController.cs` | ✏️ | ❌ | ❌ | Chỉ SV1 sửa |
| `Controllers/PostsController.cs` | ✏️ CRUD | ✏️ Cache | ❌ | **Dễ conflict!** Phối hợp |
| `Middleware/SessionAuthMiddleware.cs` | ❌ | ✏️ | ❌ | Chỉ SV2 sửa |
| `Services/*` | ❌ | ✏️ | ❌ | Chỉ SV2 sửa |
| `Models/*`, `Data/*`, `DTOs/*` | ✏️ | ❌ | ❌ | Chỉ SV1 sửa |
| `Program.cs` | ⚠️ | ⚠️ | ⚠️ | **Cẩn thận!** Ai sửa báo nhóm |
| `src/frontend/src/pages/*` | ❌ | ❌ | ✏️ | Chỉ SV3 sửa |
| `src/frontend/src/services/api.js` | ❌ | ❌ | ✏️ | Chỉ SV3 sửa |
| `scripts/*` | ❌ | ❌ | ✏️ | Chỉ SV3 sửa |

### 5.2 File dễ xung đột nhất

**`Controllers/PostsController.cs`** — cả SV1 (CRUD) và SV2 (Cache-Aside) đều sửa file này.

**Giải pháp:**
- SV1 implement `GetAll`, `Create`, `Delete` **trước**
- SV2 implement `GetById`, `Update`, `IncrementView` **sau**
- Hoặc: SV1 xong → merge vào `dev` → SV2 pull `dev` rồi mới code

### 5.3 Khi bị conflict

```bash
# Pull dev về nhánh feature
git pull origin dev

# Nếu có conflict → Git sẽ báo file nào
# Mở file → tìm <<<<<<< / ======= / >>>>>>>
# Sửa thủ công → giữ cả 2 phần code
# Sau khi sửa:
git add <file bị conflict>
git commit -m "merge: resolve conflict PostsController"
git push
```

---

## 6. Thứ tự implement đề xuất (Timeline)

```
Tuần 1:
  SV1 → AuthController (Register, Login, Logout, Me)
  SV2 → SessionAuthMiddleware
  SV3 → Seed 100 bài viết (seed.py)

       SV1 merge → dev ← SV2, SV3 pull dev

Tuần 2:
  SV1 → PostsController CRUD (GetAll, Create, Delete)
  SV2 → PostsController Cache-Aside (GetById, Update, IncrementView)
  SV3 → Frontend (HomePage, LoginPage)

       Tất cả merge → dev ← Ai cũng pull dev

Tuần 3:
  SV1 → Test + fix bug
  SV2 → Test Cache-Aside + Invalidation
  SV3 → Frontend (PostDetailPage, CreateEditPostPage) + Benchmark

       Merge dev → main → Demo
```

---

## 7. Checklist trước khi tạo Pull Request

Mỗi thành viên kiểm tra trước khi tạo PR:

- [ ] Code build thành công (`dotnet build` hoặc `npm run build`)
- [ ] Đã test thủ công qua Swagger / trình duyệt
- [ ] Không có `throw new NotImplementedException()` trong code đã implement
- [ ] Commit message theo quy ước `type(scope): mô tả`
- [ ] Đã pull mới nhất từ `dev` và không có conflict
- [ ] Không sửa file của người khác (xem bảng phân quyền ở mục 5.1)
