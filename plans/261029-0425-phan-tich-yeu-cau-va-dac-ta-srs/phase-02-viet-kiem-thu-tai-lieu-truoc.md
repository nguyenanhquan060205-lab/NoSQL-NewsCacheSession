---
phase: 2
title: "Viết bộ kiểm thử tài liệu trước (đỏ trên v2.0)"
status: complete
priority: P1
effort: "4h"
dependencies: [1]
---

# Phase 2: Viết bộ kiểm thử tài liệu trước (đỏ trên v2.0)

## Goal

Tạo `scripts/DocCheck/check_srs.py`: đọc sự thật từ code, cấu hình, số đo, CSV, docx rồi so với
`docs/SRS.md`. Bộ này phải **chạy đỏ trên SRS v2.0** và bắt được các sai lệch đã biết, trước khi
Phase 3 sửa một chữ nào trong SRS.

## Context Links

- Oracle: `reports/01-phan-tich-yeu-cau.md` (DB-xx, hợp đồng định dạng SRS v3) — từ Phase 1
- Sai lệch cần bắt: [reports/00-scout-doi-chieu-tai-lieu-voi-code.md](./reports/00-scout-doi-chieu-tai-lieu-voi-code.md) §2
- Mẫu script + test có sẵn: `scripts/Benchmark/plot.py` + `scripts/Benchmark/test_plot.py` (`unittest`, thư viện chuẩn)

## Scout trước khi làm (deep mode)

1. `git log --oneline dd9d242..HEAD -- src tests scripts docs` — code đổi thì cập nhật bảng "Sự thật lấy từ code".
2. `ls scripts/` — chắc chắn chưa ai tạo `scripts/DocCheck/`.
3. `python3 --version` ≥ 3.10 (dùng `match`/kiểu `X | Y` thì cần 3.10).

## Key Insights

- Không có `pytest`; các thư mục `scripts/*` đều dùng `python -m unittest` (`scripts/Benchmark/README.md:69`).
- Docx đọc bằng `zipfile` + regex ra 26 đoạn — đã thử khi lập plan.
- `docs/SRS.md` chưa commit. **Chụp bản v2.0 trước** khi làm bất cứ gì khác.
- SRS v3 sẽ phải nhắc lại lỗi cũ trong "Lịch sử phiên bản" và "Phụ lục F" (ví dụ "v2.0 ghi cookie
  `news_session`"). Checker phải **bỏ qua hai vùng này**, nếu không chính phần ghi nhận lỗi sẽ làm checker đỏ.

## Sự thật lấy từ code (checker tự đọc, không gõ cứng)

| Sự thật | Nguồn | Giá trị lúc lập plan |
|---|---|---|
| Endpoint | `[Route]` + `[HttpGet/Post/Put/Delete("…")]` trong `src/NewsCacheSession.Api/Controllers/*.cs`, thay `[controller]` bằng tên lớp bỏ `Controller`, chữ thường; thêm `MapHealthChecks("…")` trong `Program.cs` | 21 endpoint |
| Cookie / header phiên | `SessionCookieName`, `SessionHeaderName` trong `Services/CurrentUserService.cs:17-18` | `SessionId`, `X-Session-Id` |
| TTL | `CacheTtl`, `ListCacheTtl`, `LockTtl`, `LockWaitAttempts`, `LockWaitDelay` trong `Controllers/PostsController.cs`; `SessionSettings:TtlMinutes` trong `appsettings.json`; `_period` trong `Services/ViewCountSyncWorker.cs` | 10 phút, 3 phút, 5 s, 40, 50 ms, 30 phút, 1 phút |
| Field `/api/cache/stats` | thuộc tính `public` của lớp `CacheStats` trong `Services/ICacheService.cs`, đổi sang camelCase | `hits, misses, totalRequests, hitRate` |
| Cổng | `ports:` trong `docker-compose.yml`, `applicationUrl` trong `Properties/launchSettings.json`, `port:` trong `src/frontend/vite.config.js`, `-p NNNN:` trong `README.md` | 27017, 6379, 5540, 5134, 58320, 7295, 3000, 27019, 6380 |
| Phiên bản | `PackageReference` trong csproj, `dependencies`/`devDependencies` trong `src/frontend/package.json`, `image:` trong compose, `TargetFramework` | xem scout D7–D9 |
| Số đo | `scripts/Benchmark/results/2026-10-25-chinh-thuc/summary.json` | 5 đợt stampede, latency 3 loại, `load[].rps` |
| Jira | `docs/nosql-jira-tasks.csv` | 37 ticket |
| Đề bài | `docs/ĐỀ TÀI 06.docx` → 26 đoạn | |
| Keyspace chuẩn | bảng đầu tiên trong `docs/redis-keyspace.md` có cột `Key` + `TTL` | 7 pattern |

## 12 phép kiểm

Mỗi phép kiểm trả về danh sách lỗi dạng `[Cn] docs/SRS.md:<dòng> <mô tả> (nguồn: <file:line>)`.

| Mã | Kiểm gì | Bắt được |
|---|---|---|
| C1 | Mọi cặp `METHOD /đường-dẫn` trong SRS có trong tập endpoint của code (chuẩn hóa `{…}` → `{}`, chữ thường, bỏ `/` cuối) | D5 |
| C2 | Mọi endpoint của code xuất hiện trong SRS dưới dạng `METHOD /đường-dẫn` | thiếu `GET /api/auth/me`, chuyên mục, `/api/health` |
| C3 | Mọi token trong backtick trông như đường dẫn repo (có `/` hoặc đuôi `.cs .jsx .js .py .md .json .yml .csv .docx .ps1 .png`) tồn tại: khớp đúng từ gốc repo, hoặc khớp hậu tố với ít nhất một file. Bỏ qua token bắt đầu bằng `/` hoặc `http`, chứa `:` hay `{`. Token có `*`: chỉ cần thư mục cha tồn tại. Duyệt cây bỏ `node_modules`, `bin`, `obj`, `.git`, `dist` | D12 |
| C4 | Mọi cụm `cookie \`X\`` / `Cookie tên \`X\`` và mọi nhãn `Cookie: X` (kiểu trong sơ đồ mermaid, `docs/SRS.md:173`) có `X` bằng tên cookie trong code; SRS có nhắc `X-Session-Id` và `X-Cache` | D1 |
| C5 | Bảng keyspace của SRS có đúng tập pattern như bảng trong `docs/redis-keyspace.md` (chuẩn hóa placeholder); ô TTL chứa số khớp hằng trong code (10 phút/600, 3 phút/180, 5 giây/`EX 5`, 30 phút/1800, "Không" cho 3 key không TTL) | đổi TTL hay key |
| C6 | Khối ` ```json ` trong FR-19 có tập key bằng tập field `CacheStats` | D4 |
| C7 | Mọi `localhost:NNNN` và mọi ánh xạ cổng `` `NNNN:NNNN` `` trong SRS nằm trong tập cổng ở trên; ánh xạ của service compose phải đúng nguyên chuỗi | D6 |
| C8 | Các cụm `React N`, `Vite N`, `Tailwind N`, `MongoDB.Driver vN`, `StackExchange.Redis vN`, `` `mongo:…` ``, `` `redis:…` ``, `net8.0`/`net10.0` khớp số major/tag thật | D7–D9 |
| C9 | Bảng số đo (định dạng ở Phase 1) khớp `summary.json` sai số 0,005; cụm `N đợt` nằm trong cùng đoạn văn (hoặc cùng dòng bảng) với chữ "stampede" (không phân biệt hoa thường) bằng số phần tử `stampede`; mọi số đi với `req/s` hoặc `RPS` thuộc tập `load[].rps`, trừ số đứng sau `≥`/`>=` (ngưỡng) | D16 |
| C10 | Đủ 37 dòng `\| SCRUM-NN \|`, mỗi dòng chứa đúng trạng thái CSV; mọi cụm `N/M Jira\|ticket\|task` có `M` = 37 | D15 |
| C11 | Mọi dòng `\| DB-NN \| "…" \|` có câu trích nằm trong text docx (chuẩn hóa khoảng trắng, `–`→`-`, chữ thường). Mọi đoạn docx không phải tiêu đề phải chứa ít nhất một câu trích DB. Tiêu đề = đoạn đầu tiên, đoạn viết hoa toàn bộ, hoặc đoạn kết thúc bằng `:`. Hai đoạn được miễn, ghi chú rõ trong code: "Số lượng thành viên: 03 sinh viên", "1.0đ (Dummy Data): Bộ dữ liệu mẫu đạt chuẩn định mức bên dưới." | SRS v2.0 không có bảng DB |
| C12 | Mỗi khối `##### FR\|NFR\|IR\|DR-NN` có đủ dòng `Nguồn`, `Ưu tiên` (∈ BẮT BUỘC/NÊN/CÓ THỂ), `Phụ trách`, `Kiểm chứng` (⊆ T,D,I,A), `Test case`, có `**Tiêu chí chấp nhận**` và ít nhất một chữ "Thì". Mọi DB-xx được ít nhất một khối trỏ tới. Mọi TC được trỏ tới đều có trong danh mục và ngược lại. TC loại T: `đường/dẫn::tên` → file tồn tại (dùng bộ phân giải của C3) và `tên` có trong file (`.cs`: `\btên\s*\(`; `.js/.jsx`: chuỗi con); không có `::` thì chỉ cần file tồn tại. TC loại A/I: file bằng chứng tồn tại. TC loại D: bằng chứng trỏ tới "Phụ lục D" | định dạng v3 |

**Vùng bỏ qua** cho C1, C3, C4, C7, C8: từ tiêu đề chứa "Lịch sử phiên bản" hoặc "Phụ lục F" tới
tiêu đề cùng cấp kế tiếp.

## Giao diện dòng lệnh

```
python3 scripts/DocCheck/check_srs.py [--srs docs/SRS.md] [--repo <gốc repo>] [--only C1,C4]
```

Gốc repo mặc định = `Path(__file__).resolve().parents[2]`. In lỗi theo nhóm Cn, dòng cuối
`N lỗi / 12 phép kiểm`. Thoát `0` nếu không lỗi, `1` nếu có lỗi, `2` nếu thiếu file nguồn.

## Related Code Files

- Create: `scripts/DocCheck/check_srs.py` (~350 dòng, chỉ thư viện chuẩn)
- Create: `scripts/DocCheck/test_check_srs.py` (~300 dòng, `unittest`)
- Create: `scripts/DocCheck/README.md` (≤ 30 dòng: mục đích, lệnh chạy, chủ sở hữu Quân/SV2)
- Create: `plans/…/reports/srs-v2.0.md` (bản chụp), `plans/…/reports/02-ket-qua-do-tren-v2.txt`
- Read only: mọi file trong bảng "Sự thật lấy từ code"

## Tests Before (viết trước code checker)

`test_check_srs.py` có hai nhóm:

1. **Kín (hermetic)**: mỗi phép kiểm C1–C12 có ít nhất 1 test đạt + 1 test trượt. Dữ liệu dựng trong
   `tempfile.TemporaryDirectory()`: một controller C# nhỏ, `docker-compose.yml` nhỏ, csproj, `package.json`,
   CSV 3 dòng, docx tối giản tạo bằng `zipfile` (một `word/document.xml` có 3 đoạn), `summary.json` nhỏ.
   Ví dụ tên test: `test_c4_cookie_lech_ten_bao_loi`, `test_c4_vung_lich_su_phien_ban_duoc_bo_qua`,
   `test_c11_trich_dan_khong_co_trong_docx_bao_loi`, `test_c12_tc_tro_toi_method_khong_ton_tai_bao_loi`.
2. **Repo thật** (chặn extractor lệch code): `facts_from_code(REPO)` trả cookie `SessionId`, đúng 21 endpoint
   gồm `POST /api/images` và `GET /api/auth/me`, field stats `{hits, misses, totalRequests, hitRate}`, 37 ticket, 26 đoạn docx.

Chạy trước khi viết checker — phải đỏ vì chưa có module (`ModuleNotFoundError`):

```bash
cd /Users/quan/HUIT_CNTT/NoSQL/NoSQL-NewsCacheSession
python3 -m unittest discover -s scripts/DocCheck -p 'test_*.py' -v
```

## Implementation Steps

1. Chụp v2.0: `cp docs/SRS.md plans/261029-0425-phan-tich-yeu-cau-va-dac-ta-srs/reports/srs-v2.0.md`.
2. Viết `test_check_srs.py` (Tests Before), chạy, xác nhận đỏ.
3. Viết `check_srs.py`: hàm `facts_from_code(repo)`, hàm `load_srs(path)` (trả dòng + vùng bỏ qua),
   12 hàm `check_c1` … `check_c12(srs, facts) -> list[str]`, `main()`.
4. Chạy unit test tới khi xanh.
5. Chạy đỏ trên v2.0:
   ```bash
   python3 scripts/DocCheck/check_srs.py --srs plans/261029-0425-phan-tich-yeu-cau-va-dac-ta-srs/reports/srs-v2.0.md \
     > plans/261029-0425-phan-tich-yeu-cau-va-dac-ta-srs/reports/02-ket-qua-do-tren-v2.txt; echo "exit=$?"
   ```
   Mong đợi `exit=1`, và file kết quả chứa: `news_session` (C4), `totalLookups` (C6), `/api/images/upload` (C1),
   `8001` (C7), `CacheBadge.jsx` (C3), `49/49` (C10).
6. Viết `README.md`.

## Todo

- [x] Chụp `reports/srs-v2.0.md`
- [x] Tests Before đỏ vì chưa có module
- [x] `check_srs.py` đủ C1–C12, vùng bỏ qua
- [x] Unit test xanh
- [x] Chạy đỏ trên v2.0 bắt đủ 6 sai lệch mốc
- [x] `README.md`

## Test Scenario Matrix

| Mức | Kịch bản | Test |
|---|---|---|
| Critical | Cookie/cổng/endpoint/field stats sai → phải đỏ | hermetic C1, C4, C6, C7 (trượt) |
| Critical | Ghi lỗi cũ trong "Lịch sử phiên bản" không được làm đỏ | `test_c4_vung_lich_su_phien_ban_duoc_bo_qua` |
| Critical | Extractor lệch code thật | nhóm repo thật |
| High | Trích dẫn đề bài sai chữ | hermetic C11 |
| High | TC trỏ tới test không tồn tại | hermetic C12 |
| Medium | Đường dẫn tương đối kiểu `Controllers/AuthController.cs` được coi là có | hermetic C3 (khớp hậu tố) |
| Medium | Số ngưỡng `≥ 800 req/s` không bị coi là số đo | hermetic C9 |

## Success Criteria

- `python3 -m unittest discover -s scripts/DocCheck -p 'test_*.py' -v` xanh, ≥ 26 test.
- Chạy trên `reports/srs-v2.0.md` thoát `1` và bắt đủ 6 sai lệch mốc ở bước 5.

## Risk Assessment

- Regex bắt nhầm (ví dụ giờ `11:20` bị coi là ánh xạ cổng) → C7 chỉ xét token trong backtick, hai vế ≥ 4 chữ số.
- `[controller]` viết hoa/thường khác nhau → so khớp chữ thường.
- Hậu tố trùng nhiều file (`CLAUDE.md` có ở 3 nơi) → C3 chỉ cần ≥ 1 kết quả.

## Security Considerations

- Checker chỉ kiểm **sự tồn tại** của file, không đọc hay in nội dung file ngoài danh sách nguồn.
  Không đọc `.env*`, `docs/atlas-credentials.env` (`.gitignore:8-9`).

## Refactor

Không đụng code sẵn có. Thư mục mới `scripts/DocCheck/` thuộc Quân (SV2) — báo nhóm vì `scripts/` phần lớn là của SV3.

## Tests After

Không có hành vi mới ngoài checker; Tests Before chính là test của phase.

## Regression Gate

```bash
python3 -m unittest discover -s scripts/DocCheck -p 'test_*.py' -v
```

## Next Steps

Phase 3 sửa SRS cho tới khi `check_srs.py` thoát `0`.
