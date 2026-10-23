# Khôi phục toàn bộ dữ liệu bài viết

Hai file Extended JSON nén chứa bản sao đầy đủ của dữ liệu đang chạy:

- `data/newsdb-posts.json.gz`
- `data/newsdb-categories.json.gz`

- `newsdb.posts`: 10.251 document, gồm 10.150 bài đang hiển thị và 101 bài xóa mềm.
- `newsdb.categories`: 7 document.
- Không chứa `users`, mật khẩu hoặc session.

SHA-256:

```text
newsdb-posts.json.gz:
C9B4D29D2CC2017E6DD1A1A41BE73178754B710C5F899CB8ED9BB247C5B7E6C1

newsdb-categories.json.gz:
A44A4BC3C671B0BA055DEB2BD94EA08D7C2231030DE99D4C8828EA52D84E3393
```

## Máy thành viên sau khi pull

Chạy từ thư mục gốc repository:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/SeedPosts/restore_full_data.ps1 -ConfirmReplace
```

Script thực hiện theo thứ tự:

1. Khởi động MongoDB và Redis của dự án.
2. Ghi `posts` và `categories` vào MongoDB bằng `mongoimport --drop`.
3. Giữ nguyên collection `users`.
4. Xóa Redis DB sau khi MongoDB thành công để cache được tạo lại từ dữ liệu mới.
5. In số document để xác minh.

> Cảnh báo: `--drop` thay thế toàn bộ `posts` và `categories` hiện có trên máy chạy lệnh.

## Khôi phục lên MongoDB cloud

Cài MongoDB Database Tools, giải nén rồi nhập từng collection:

```powershell
$env:MONGODB_URI = "<MongoDB cloud URI>"
gzip -dc scripts/SeedPosts/data/newsdb-categories.json.gz | mongoimport --uri="$env:MONGODB_URI" --db=newsdb --collection=categories --drop
gzip -dc scripts/SeedPosts/data/newsdb-posts.json.gz | mongoimport --uri="$env:MONGODB_URI" --db=newsdb --collection=posts --drop
```

Không commit URI, mật khẩu hoặc API key vào Git. Redis cloud không cần nhập dữ liệu cũ vì cache sẽ tự tạo lại.
