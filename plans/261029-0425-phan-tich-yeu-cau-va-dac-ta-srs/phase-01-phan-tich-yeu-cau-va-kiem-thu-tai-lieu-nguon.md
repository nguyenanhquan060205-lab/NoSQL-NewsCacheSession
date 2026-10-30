---
phase: 1
title: "Phân tích yêu cầu và kiểm thử tài liệu nguồn"
status: complete
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: Phân tích yêu cầu và kiểm thử tài liệu nguồn

## Goal

Tách đề bài 06 và CSV Jira thành danh sách yêu cầu nguyên tử có ID, chốt cách xử lý mọi mâu thuẫn
giữa các nguồn, và chốt hợp đồng định dạng SRS v3 mà checker ở Phase 2 sẽ đọc.

## Context Links

- Scout: [reports/00-scout-doi-chieu-tai-lieu-voi-code.md](./reports/00-scout-doi-chieu-tai-lieu-voi-code.md) (D1–D23, S1–S9)
- Nguồn: `docs/ĐỀ TÀI 06.docx`, `docs/nosql-jira-tasks.csv`
- Đã khớp code: `docs/redis-keyspace.md`, `docs/mongodb-schema.md`
- Số đo: `scripts/Benchmark/results/2026-10-25-chinh-thuc/{summary,env,stampede}.json`, `docs/bao-cao-kiem-thu-hieu-nang.md`

## Key Insights

- Đọc docx bằng thư viện chuẩn được: `zipfile` + regex trên `word/document.xml` ra đúng 26 đoạn
  (đã thử lúc lập plan). Checker dùng lại cách này, không cần `python-docx`.
- Đề bài chỉ cho điểm con ở phần 1 (1.0 + 1.5) và phần 4 (1.0 + 1.5). Phần 2 và phần 3 **không có
  điểm con**. Ma trận barem của SRS v2.0 tự đặt ra 1.0/1.5 và 1.25/1.25 (`docs/SRS.md:791-795`).
  Đây là sai lệch D24, SRS v3 không được tự chia điểm.
- Đề bài nhắc "Apache Benchmark", còn nhóm đo bằng `scripts/Benchmark/benchmark.py`. SRS phải ghi
  rõ công cụ thay thế và lý do (S10). Kiểm `scripts/Benchmark/README.md` trước khi viết lý do.
- CSV chỉ có SCRUM-13 → 49. SCRUM-01…12 nằm ở `docs/SCRUM-07-11.md` (dựng khung). Ma trận truy vết
  chỉ bắt buộc 37 ticket trong CSV.

## Requirements

Chức năng của phase:
1. Danh sách DB-01…DB-19. Mỗi mục trích **nguyên văn** một đoạn trong docx kèm điểm barem nếu có.
2. Bảng 37 ticket CSV gồm: trạng thái CSV, DB-xx liên quan, yêu cầu SRS liên quan, bằng chứng trong repo.
3. Bảng quyết định cho S1–S10 và D24.
4. Kho yêu cầu SRS v3 (FR/NFR/DR/IR) có nguồn và phương pháp kiểm chứng.
5. Hợp đồng định dạng SRS v3.

Phi chức năng: kết quả nằm trong một file `reports/01-phan-tich-yeu-cau.md`, mọi khẳng định có `file:line`.

## Bản nháp DB-xx (đã khớp với 26 đoạn docx)

| ID | Trích nguyên văn (một đoạn con) | Điểm |
|---|---|---|
| DB-01 | "Trang tin tức trực tuyến có phân hệ đăng nhập, đọc bài viết; hệ thống tích hợp bộ nhớ đệm để tăng tốc độ tải trang." | — |
| DB-02 | "Hệ quản trị CSDL chính: Redis (Phối hợp MongoDB / MySQL làm DB gốc)" | — |
| DB-03 | "Trình bày rõ nguyên lý hoạt động của kiến trúc bộ nhớ đệm Cache-Aside Pattern." | 1.0 |
| DB-04 | "Thiết kế mô hình dữ liệu Hashes cho Session, Strings/Hashes cho Cache bài viết và cơ chế khóa." | 1.5 |
| DB-05 | "Đăng ký/đăng nhập" | phần 2: 2.5 chung |
| DB-06 | "viết bài mới, sửa/xóa bài viết trên CSDL chính" | phần 2: 2.5 chung |
| DB-07 | "Nếu Cache Miss thì gọi DB gốc rồi ghi ngược lại Redis kèm TTL (EXPIRE)." | phần 3: 2.5 chung |
| DB-08 | "Khi sửa bài viết, tự động xóa Cache liên quan (Cache Invalidation)." | phần 3 |
| DB-09 | "Dùng cấu trúc Hashes lưu Session người dùng" | phần 3 |
| DB-10 | "dùng lệnh INCR xử lý bộ đếm lượt xem bài viết tăng tiến thời gian thực." | phần 3 |
| DB-11 | "Tối thiểu 100 Bài viết hoàn chỉnh có tiêu đề, nội dung và hình ảnh." | 1.0 chung với DB-12 |
| DB-12 | "Tối thiểu 20–50 Session/Cache Keys lưu tại Redis có thiết lập TTL khác nhau." | 1.0 chung với DB-11 |
| DB-13 | "SV3 mở tab Network (F12) tải bài viết lần 1 (đọc DB gốc ~200ms) vs lần 2 (đọc Redis <5ms)." | 1.5 chung (demo) |
| DB-14 | "SV2 chứng minh Cache cũ bị xóa ngay lập tức (Cache Invalidation)." | 1.5 chung (demo) |
| DB-15 | "SV3 mở Redis Insight chỉ ra Key Session tự động đếm lùi thời gian sống (TTL)." | 1.5 chung (demo) |
| DB-16 | "đo lường và vẽ biểu đồ so sánh thời gian tải qua tab Network F12 / Apache Benchmark" | — (phân công SV3) |
| DB-17 | "Thực hiện trơn tru các bước trong kịch bản demo bảo vệ." | 1.5 |
| DB-18 | "Thiết kế cấu trúc DB gốc và mô hình Hashes/Strings trên Redis; viết API CRUD bài viết trên DB gốc." | — (phân công SV1) |
| DB-19 | "Xây dựng Middleware Cache-Aside, xử lý TTL (EXPIRE), Cache Invalidation và bộ đếm INCR." | — (phân công SV2; đoạn SV3 đã có DB-16) |

Ô trích dẫn chỉ chứa câu trích trong `"…"`, không thêm chữ sau dấu đóng ngoặc — Tests Before đọc
đúng mẫu `| DB-NN | "…" |`.

## Kho yêu cầu SRS v3 (giữ nguyên ID FR-01…FR-21 của v2.0 để không gãy tham chiếu)

| ID | Nội dung | Nguồn | Kiểm chứng |
|---|---|---|---|
| FR-01 | Đăng ký, admin đầu tiên giành bằng `meta._id = bootstrapAdmin` | DB-05, SCRUM-13 | T |
| FR-02 | Đăng nhập: Hash 5 field + `EXPIRE` trong một `MULTI/EXEC`, cookie `SessionId` | DB-05, DB-09, SCRUM-13/14 | T |
| FR-03 | Middleware đọc cookie hoặc `X-Session-Id`, sliding TTL, cấp lại cookie | DB-09, SCRUM-15 | T |
| FR-04 | Đăng xuất xóa `session:{id}` | DB-05, SCRUM-13 | T |
| FR-05 | Admin liệt kê (SCAN) và thu hồi phiên | DB-15, SCRUM-31 | T, D |
| FR-06 | Tạo bài, slug tiếng Việt, hậu tố `-2, -3…`, thử lại ≤ 3 lần rồi 409, `INCR posts:ver` | DB-06, SCRUM-16 | T |
| FR-07 | Sửa bài: quyền admin/tác giả, giữ slug, ghi Mongo rồi `DEL post:{id}` + `INCR posts:ver` | DB-06, DB-08, SCRUM-16/23 | T |
| FR-08 | Xóa mềm, giữ `post:{id}:views` | DB-06, DB-08, SCRUM-17/23 | T |
| FR-09 | Danh sách: `page`, `pageSize` 1–50 (mặc định 10), lọc `categoryId` | DB-01, SCRUM-18 | T |
| FR-10 | `GET /api/posts/slug/{slug}` cố ý không cache (mốc đối chứng) | DB-13, SCRUM-19 | T |
| FR-11 | Chuyên mục: 3 endpoint đọc + tạo (admin) | DB-06, SCRUM-18 | T, I |
| FR-12 | Cache-Aside ở `GET /api/posts/{id}`, TTL 600 s, header `X-Cache` | DB-07, SCRUM-20/21 | T |
| FR-13 | Khóa `lock:post:{id}` TTL 5 s, chờ 40 × 50 ms rồi đọc thẳng Mongo không ghi cache | DB-04, SCRUM-24 | T |
| FR-14 | Invalidation khi sửa/xóa | DB-08, DB-14, SCRUM-23 | T, D |
| FR-15 | Cache danh sách `posts:cat:{cat\|all}:p{n}:v{ver}`, TTL 180 s, lệch `pageSize` coi là MISS | DB-07, SCRUM-26 | T |
| FR-16 | `INCR posts:ver` thay SCAN + DEL | DB-08, SCRUM-26 | T, I |
| FR-17 | `POST /api/posts/{id}/view`: khởi tạo `SET NX` từ `posts.views`, `INCR`, `SADD posts:dirty_views`, 404 nếu bài không tồn tại | DB-10, SCRUM-25 | T |
| FR-18 | Worker mỗi 60 s: `SCARD` + `SPOP n`, ghi `posts.views`, lỗi thì `SADD` lại phần còn lại | DB-10, SCRUM-25 | T |
| FR-19 | `GET /api/cache/stats` → `hits, misses, totalRequests, hitRate` | DB-16, SCRUM-34 | T |
| FR-20 | `/health` và `/api/health` (503 khi không Healthy) | DB-02 | T |
| FR-21 | `POST /api/images`: jpeg/png/webp ≤ 5 MB, REST Cloudinary; cờ `PostingSettings:AdminOnly` | DB-11, SCRUM-39 | T, I |
| FR-22 | `GET /api/auth/me` trả `expiresInSeconds` | DB-15, SCRUM-13/30 | T |
| IR-01…IR-05 | Trang chủ, chi tiết + badge `X-Cache`, đăng nhập, admin bài viết, admin phiên | DB-01, DB-13, SCRUM-22/27/29/30/31/38 | T (Vitest), D |
| NFR-01 | HIT ≤ 5 ms (đo được 2,96 ms) | DB-13 | A |
| NFR-02 | MISS đọc Mongo rồi ghi Redis; HIT < MISS; số đo kèm giải thích vì sao không phải ~200 ms | DB-13 | A |
| NFR-03 | 50 request đồng thời vào key lạnh → đúng 1 MISS | DB-04 | T, A |
| NFR-04 | ≥ 800 req/s ở 50 luồng, 0 lỗi (nhóm tự đặt, ưu tiên NÊN) | nội bộ | A |
| NFR-05 | Redis sập: đọc công khai vẫn chạy từ Mongo, thao tác cần Redis trả 503 | nội bộ | T |
| NFR-06 | Bảo mật: `HttpOnly`, `SameSite=Lax`, `Secure` theo scheme, BCrypt, token khóa riêng từng request | nội bộ | T, I |
| NFR-07 | Nhất quán: ghi Mongo trước, xóa Redis sau; xóa cache trước khi gọi Cloudinary | DB-08 | T |
| NFR-08 | Kiểm thử được: test tự động + checker tài liệu | nội bộ | I |
| NFR-09 | Ràng buộc nghiệm thu: có chương báo cáo nguyên lý Cache-Aside, phân công 3 SV theo đề bài, demo 3 bước chạy trơn tru | DB-03, DB-16, DB-17, DB-18, DB-19 | I, D |

Kiểm tra phủ: mỗi DB-01…DB-19 phải nằm trong cột Nguồn của ít nhất một dòng ở bảng này (C12 kiểm lại trên SRS).
| DR-01…DR-03 | 4 collection Mongo + 5 index; keyspace 7 pattern; dummy data ≥ 100 bài, 20–50 key TTL khác nhau | DB-02, DB-04, DB-11, DB-12, SCRUM-32/33/36 | I, T, A |

## Hợp đồng định dạng SRS v3 (checker Phase 2 đọc đúng các mẫu này)

1. Bảng yêu cầu nguồn: dòng bắt đầu `| DB-NN |`, cột 2 là trích nguyên văn trong ngoặc kép `"…"`.
2. Khối yêu cầu: tiêu đề `##### FR-NN: …` / `##### NFR-NN: …` / `##### IR-NN: …` / `##### DR-NN: …`.
   Ngay dưới là bảng `| Thuộc tính | Giá trị |` có đủ các dòng `Nguồn`, `Ưu tiên`, `Phụ trách`,
   `Kiểm chứng`, `Test case`. Sau đó là `**Mô tả**` và `**Tiêu chí chấp nhận**`, mỗi tiêu chí viết
   theo dạng *Cho … / Khi … / Thì …*.
3. Danh mục test case: dòng `| TC-NN | <T\|D\|I\|A> | <bằng chứng> | <ID yêu cầu> |`. Với phương pháp T,
   bằng chứng là `` `đường/dẫn/File.cs::TenMethod` `` hoặc `` `đường/dẫn/x.test.jsx::tên test` ``.
4. Ma trận Jira: `| SCRUM-NN | … | <phụ trách> | <trạng thái CSV> | <bằng chứng> | <ID yêu cầu> |`.
5. Bảng keyspace: hàng tiêu đề chứa `Key` và `TTL`.
6. Bảng số đo: hàng tiêu đề `| Chỉ số | Không cache | Cache MISS | Cache HIT |`, các dòng `Mean`, `P50`,
   `P95`, `P99`, `Min`. Số viết dấu phẩy hoặc dấu chấm thập phân đều được.
7. JSON mẫu của `/api/cache/stats` nằm trong khối ` ```json ` thuộc FR-19.

## Related Code Files

- Create: `plans/261029-0425-phan-tich-yeu-cau-va-dac-ta-srs/reports/01-phan-tich-yeu-cau.md`
- Read only: mọi file trong Context Links, `src/**`, `tests/**`, `scripts/**`

## Tests Before (viết trước, chạy được ngay trên kết quả phân tích)

Viết `reports/01-phan-tich-yeu-cau.md` rồi chạy đoạn kiểm tra dưới đây. Nó kiểm tra chính bản phân
tích, chưa đụng tới SRS:

```bash
cd /Users/quan/HUIT_CNTT/NoSQL/NoSQL-NewsCacheSession
python3 -I - <<'EOF'
import csv, html, re, zipfile, pathlib
plan = pathlib.Path("plans/261029-0425-phan-tich-yeu-cau-va-dac-ta-srs/reports/01-phan-tich-yeu-cau.md").read_text()
x = zipfile.ZipFile("docs/ĐỀ TÀI 06.docx").read("word/document.xml").decode()
doc = " ".join(html.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)))
               for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S))
norm = lambda s: re.sub(r"\s+", " ", s.replace("–", "-")).strip().lower()
rows = re.findall(r'^\| (DB-\d\d) \| "(.+?)" \|', plan, re.M)
assert len(rows) == 19, f"cần 19 DB-xx, có {len(rows)}"
bad = [i for i, q in rows if norm(q) not in norm(doc)]
assert not bad, f"trích dẫn không có trong docx: {bad}"
keys = [r["Key"] for r in csv.DictReader(open("docs/nosql-jira-tasks.csv"))]
missing = [k for k in keys if f"| {k} |" not in plan]
assert not missing, f"ticket chưa phân tích: {missing}"
print("OK", len(rows), "DB-xx,", len(keys), "ticket")
EOF
```

Kết quả mong đợi: `OK 19 DB-xx, 37 ticket`.

## Implementation Steps

1. Scout lại: `git log --oneline dd9d242..HEAD -- src tests scripts docs`. Có thay đổi thì xác minh lại
   từng dòng D1–D23 bằng `grep -n` và cập nhật `reports/00-…`.
2. Trích 26 đoạn docx bằng đoạn mã ở trên (bỏ `assert`), dán bảng DB-01…DB-19 vào report.
3. Đọc CSV, viết bảng 37 ticket. Với ticket không Done, tìm bằng chứng trong repo bằng
   `git log --oneline --grep "SCRUM-NN"` và `ls` file liên quan.
4. Viết bảng quyết định S1–S10 và D24, mỗi dòng: mâu thuẫn, nguồn A, nguồn B, quyết định, lý do.
5. Chép kho yêu cầu và hợp đồng định dạng ở trên vào report. Sửa nếu bước 1–4 làm lộ chỗ sai.
6. Chạy Tests Before, sửa report tới khi in ra `OK`.

## Todo

- [x] Scout lại thay đổi sau `dd9d242`
- [x] Bảng DB-01…DB-19 trích nguyên văn
- [x] Bảng 37 ticket có bằng chứng repo
- [x] Bảng quyết định S1–S10, D24
- [x] Kho yêu cầu + hợp đồng định dạng
- [x] Tests Before in `OK 19 DB-xx, 37 ticket`

## Test Scenario Matrix

| Mức | Kịch bản | Cách kiểm |
|---|---|---|
| Critical | Trích dẫn đề bài bị chép sai chữ | Tests Before: so khớp với text docx |
| Critical | Bỏ sót ticket CSV | Tests Before: đủ 37 key |
| High | Tự chia điểm barem không có trong đề | Đọc lại bảng DB-xx: cột điểm chỉ dùng số có trong docx |
| Medium | Ticket "Idea" nhưng thật ra đã xong | Bước 3: phải có commit hoặc file làm bằng chứng |

## Success Criteria

- Tests Before in `OK 19 DB-xx, 37 ticket`.
- Mọi quyết định S1–S10, D24 có lý do và dẫn nguồn.

## Risk Assessment

- Trích dẫn có ký tự đặc biệt (`–`, `~`, `<`) → hàm chuẩn hóa đổi `–` thành `-`. Không tự "sửa đẹp" câu trích.
- Bằng chứng cho ticket Idea mơ hồ → ghi "không tìm thấy bằng chứng", không đoán.

## Security Considerations

- Không chép nội dung `docs/atlas-credentials.env`, `.env.render` vào report (bị `.gitignore` chặn, chứa chuỗi kết nối).

## Refactor

Không có — phase này không sửa file nào ngoài report.

## Regression Gate

Đoạn Tests Before ở trên.

## Next Steps

Phase 2 dùng bảng DB-xx và hợp đồng định dạng làm oracle cho kiểm tra C11 và C12.
