---
title: "Phân tích yêu cầu và đặc tả SRS cho phân hệ Caching & Session"
description: "Dựng lại docs/SRS.md v3.0 từ đề bài 06 và Jira CSV, mọi khẳng định được kiểm thử tự động với code, cấu hình, test và số đo thật."
status: complete
priority: P1
effort: 16h
branch: develop
tags: [docs, backend, database, critical]
blockedBy: []
blocks: []
created: 2026-10-29
---

# Phân tích yêu cầu và đặc tả SRS — phân hệ Caching & Session

## Overview

`docs/SRS.md` v2.0 (chưa commit) tự nhận "đồng bộ 100% với mã nguồn" nhưng scout tìm ra 23 chỗ
sai so với code. Có chỗ làm hỏng demo: cookie `news_session` (thật là `SessionId`), RedisInsight
cổng 8001 (thật là 5540), `/api/cache/stats` sai toàn bộ tên field, "49/49 Jira" (CSV chỉ có 37
ticket, 11 ticket chưa Done). Plan này phân tích lại yêu cầu từ nguồn rồi viết **bộ kiểm thử tài
liệu trước** (`scripts/DocCheck/`). Bộ này phải chạy đỏ trên v2.0, sau đó mới viết lại SRS v3.0 cho
tới khi xanh, cuối cùng kiểm chứng trên hệ thống chạy thật.

Bằng chứng scout: [reports/00-scout-doi-chieu-tai-lieu-voi-code.md](./reports/00-scout-doi-chieu-tai-lieu-voi-code.md).

## Hợp đồng đầu ra (brainstorm contract)

| | |
|---|---|
| **Kết quả** | `docs/SRS.md` v3.0: mọi yêu cầu có ID, nguồn (đề bài/SCRUM), ưu tiên, tiêu chí chấp nhận, phương pháp kiểm chứng (T/D/I/A theo ISO/IEC/IEEE 29148) và test case trỏ tới test thật. Kèm `scripts/DocCheck/` kiểm thử SRS với code |
| **Ràng buộc** | Chỉ sửa `docs/SRS.md` và tạo file mới trong `scripts/DocCheck/` + thư mục plan. Không sửa `src/`, không sửa tài liệu của SV1/SV3, không sửa CSV Jira. Python chỉ dùng thư viện chuẩn + `unittest` (máy không có `pytest`). Tiếng Việt, cấu trúc IEEE 830 |
| **Không làm** | Không thêm hay sửa tính năng. Không chạy lại benchmark chính thức (dùng số đo 25/10). Không xuất DOCX/PDF. Không đăng nhập hay ghi gì lên bản deploy. Không commit khi chưa được Quân đồng ý |
| **Chấp nhận** | (1) `check_srs.py` thoát mã ≠ 0 trên v2.0 và báo được ít nhất D1, D4, D5, D6, D12, D15. (2) Thoát mã 0 trên v3.0. (3) Bộ unit test của checker xanh. (4) 19 yêu cầu đề bài (DB-01…DB-19, trích nguyên văn, đã khớp docx khi lập plan) và 37 ticket CSV đều có trong ma trận truy vết. (5) Phase 4 có báo cáo kiểm thử thật kèm output lệnh |

Scope: **HOLD** (không có `--yagni`). Mode: `--deep` + `--tdd`. Phase 1 chi tiết; Phase 2–4 mỗi
phase scout lại code trước khi làm vì code có thể đổi sau 29/10.

## Phases

| # | Phase | Effort | Phụ thuộc | Status |
|---|-------|--------|-----------|--------|
| 1 | [Phân tích yêu cầu và kiểm thử tài liệu nguồn](./phase-01-phan-tich-yeu-cau-va-kiem-thu-tai-lieu-nguon.md) | 3h | — | Complete |
| 2 | [Viết bộ kiểm thử tài liệu trước (đỏ trên v2.0)](./phase-02-viet-kiem-thu-tai-lieu-truoc.md) | 4h | 1 | Complete |
| 3 | [Viết lại SRS v3.0 cho tới khi xanh](./phase-03-viet-lai-srs-v3.md) | 6h | 2 | Complete |
| 4 | [Kiểm thử trên hệ thống chạy thật và chốt](./phase-04-kiem-thu-tren-he-thong-that-va-chot.md) | 3h | 3 | Complete |

## Bản đồ phụ thuộc

```
Phase 1 ── reports/01-phan-tich-yeu-cau.md (DB-xx, kho yêu cầu, hợp đồng định dạng SRS v3)
   │            └─ là "oracle" cho kiểm tra C11, C12 của checker
   ▼
Phase 2 ── scripts/DocCheck/check_srs.py + test_check_srs.py  →  chạy đỏ trên v2.0
   ▼
Phase 3 ── docs/SRS.md v3.0  →  checker xanh
   ▼
Phase 4 ── stack thật: dotnet test, NEWS_IT=1, vitest, unittest, kiểm tra sống L6–L15 (local), L16–L20 (deploy, chỉ GET)
```

## Kho file

| File | Hành động | Cỡ | Ảnh hưởng test |
|---|---|---|---|
| `docs/SRS.md` | Viết lại (v2.0 → v3.0) | ~900 dòng | Đối tượng của checker |
| `scripts/DocCheck/check_srs.py` | Tạo | ~350 dòng | Mới |
| `scripts/DocCheck/test_check_srs.py` | Tạo | ~300 dòng | Mới, `unittest` |
| `plans/…/reports/01-…`, `02-…`, `04-…` | Tạo | — | Bằng chứng |

## Rủi ro chính

- `docs/SRS.md` chưa commit, mất là mất v2.0 → Phase 2 chụp bản v2.0 vào `reports/srs-v2.0.md` trước khi sửa.
- Docker đang tắt → Phase 4 phải bật stack. Container QA dùng cổng riêng 27019/6380, dọn sau khi xong.
- `scripts/` phần lớn là của SV3 → `scripts/DocCheck/` là thư mục mới, ghi rõ chủ sở hữu là Quân và báo nhóm.

- Phase 3 có thể vượt 6h: 22 FR + 9 NFR, mỗi khối kèm bảng thuộc tính, cộng 55 TC → viết theo
  từng phần, chạy `--only` sau mỗi phần (bảng Refactor của Phase 3).

## Red Team Review

Chạy inline 4 góc nhìn (Assumption, Failure Mode, Scope, Security) trên 4 phase, 29/10. Mọi phát hiện
dưới đây có bằng chứng `file:line` hoặc lệnh đã chạy.

| # | Mức | Phát hiện | Bằng chứng | Kết luận |
|---|---|---|---|---|
| RT1 | High | Phân công chỉ có câu SV2 → đoạn SV1 trong docx không được câu trích nào phủ, C11 sẽ đỏ mãi | Mô phỏng C11 trên 26 đoạn docx | **Áp dụng**: tách DB-18 (SV1), DB-19 (SV2); mô phỏng lại: phủ đủ |
| RT2 | High | DB-03 (báo cáo Cache-Aside) không thuộc khối yêu cầu nào → C12 đỏ | Phase 1, bảng kho yêu cầu | **Áp dụng**: NFR-09 nhận DB-03; kiểm lại: 19/19 DB được phủ |
| RT3 | High | C4 không bắt được nhãn mermaid `Cookie: news_session` (không có backtick) | `docs/SRS.md:173` | **Áp dụng**: C4 thêm mẫu `Cookie: X` |
| RT4 | Medium | Máy không có `redis-cli` → lệnh Phase 4 chạy không được | `which redis-cli` → not found | **Áp dụng**: dùng `docker exec <container> redis-cli` |
| RT5 | Medium | "N đợt gần chữ stampede" mơ hồ, dễ bắt nhầm | Phase 2, C9 | **Áp dụng**: cùng đoạn văn hoặc cùng dòng bảng |
| RT6 | Medium | `MONITOR` hay login trên Redis demo sẽ in token phiên thật | `src/NewsCacheSession.Api/Services/RedisSessionService.cs:16` (key chứa sessionId) | Đã có trong Phase 4: thao tác ghi và `MONITOR` chỉ trên QA |
| RT7 | Medium | Checker duyệt cây file có `.env.render`, `docs/atlas-credentials.env` | `.gitignore:8-9` | Không đổi: C3 chỉ kiểm sự tồn tại, không đọc nội dung (đã ghi ở Phase 2) |
| RT8 | Medium | Cổng 27017 có thể bị Mongo Homebrew chiếm | `plans/261025-1501-…/reports/03-e2e-va-dien-tap.md:61` | Đã có trong Phase 4 scout bước 3: hỏi trước khi dừng |
| RT9 | Low | Test "repo thật" khẳng định đúng 21 endpoint sẽ đỏ khi có người thêm endpoint | Phase 2 Tests Before nhóm 2 | Giữ: đỏ là đúng ý, buộc cập nhật SRS. Ghi vào README của checker |

Bác bỏ: "đề bài có thể đổi" — không có bằng chứng, docx là đề cố định.

### Whole-Plan Consistency Sweep

- Đã tìm lại trong mọi file plan các cụm cũ `DB-01…DB-17`, `18 DB`, `17 yêu cầu`, `NFR-05…08`,
  `redis-cli -p`: không còn.
- Đã kiểm 44 tham chiếu `File.cs::Method` trong Phase 3 với code test: 44/44 có thật.
- Đường dẫn còn "không tồn tại" đều là chủ ý: tên sai cần bắt (`CacheBadge.jsx`), file sẽ tạo
  (`scripts/DocCheck/*`, `reports/01-…`, `reports/srs-v2.0.md`), hoặc mẫu giữ chỗ.
- Không còn mâu thuẫn chưa giải quyết.

## Validation Log

### Quyết định của Quân (29/10)

| Câu hỏi | Chọn |
|---|---|
| Xử lý `docs/SRS.md` v2.0 | Viết đè thành v3.0, chụp v2.0 vào `reports/srs-v2.0.md` trước |
| Nơi đặt bộ kiểm thử tài liệu | `scripts/DocCheck/` (thư mục mới của Quân, báo nhóm) |
| Kiểm thử sống | Cả hai: Docker local (ghi trên QA, đọc trên demo) + GET chỉ đọc lên bản deploy → thêm L16–L20 vào Phase 4 |

### Verification Results

- Claims checked: 63 (44 tham chiếu `File.cs::Method`, 19 câu trích đề bài)
- Verified: 63 | Failed: 0 | Unverified: 0
- Tier: Standard (4 phase — Fact Checker + Contract Verifier)
- Kiểm thêm: 21 endpoint đếm từ code; quét đường dẫn trong mọi file plan (chỉ còn đường dẫn cố ý sai hoặc sẽ tạo);
  `ak plan validate` → OK.
