---
title: "Kiểm thử ổn định toàn hệ thống (flow SV1–SV2–SV3) và deploy miễn phí"
description: "Chứng minh bằng test thật (Redis + MongoDB thật) rằng toàn bộ flow của Như, Quân, Định chạy ổn định, sửa lỗi đã chứng minh, rồi deploy Render + Atlas + Redis Cloud + Vercel."
status: in-progress
priority: P1
effort: 24.5h
branch: develop
tags: [backend, frontend, critical, infra]
blockedBy: []
blocks: []
created: 2026-10-25
---

# Kiểm thử ổn định toàn hệ thống và deploy

## Overview

Test có sẵn đều xanh (.NET 27/27, Vitest 103/103), nhưng test .NET dùng mock 100% và `main` trên
GitHub còn không build được project test (G27). Plan này kiểm thử trên **môi trường QA tách biệt**,
phủ đủ flow của Như (SV1), Quân (SV2), Định (SV3), sửa các lỗi đã được chứng minh, đưa `develop`
lên `main`, rồi mới deploy.

Danh sách nghi vấn G1–G28 kèm file:line: [reports/00-gia-thuyet-tu-doc-code.md](./reports/00-gia-thuyet-tu-doc-code.md).

## Quyết định đã chốt (25/10)

| Chủ đề | Quyết định |
|---|---|
| Nhánh | Làm hết trên `develop` (đã tạo, commit `9665335`); xong Phase 5 mới mở PR `develop → main` |
| Sửa file người khác | **Phương án B**: lỗi chặn demo/barem trong file của Như/Định/file dùng chung → nhắn nhóm xin phép rồi sửa; lỗi nhỏ → gửi báo cáo cho chủ file |
| Lỗi Redis sập | Sửa triệt để ngay trong Phase 5 (không hoãn); hạn 26/10 chỉ là mốc ước tính |
| Cổng 27017 | Được dừng Mongo Homebrew để container đồ án dùng 27017 đúng README (Phase 3) |
| Môi trường QA | `news-mongo-qa:27019`, `news-redis-qa:6380` (không lưu đĩa), API `:5135`, Vite `:3001`; không đụng stack demo |
| Deploy | Sau khi kiểm thử + sửa xong: Render (Docker) + **MongoDB Atlas M0** + Redis Cloud free + Vercel |
| Commit | Tiếng Việt, mã ticket gốc, **không** dòng `Co-Authored-By` (theo `AGENTS.md`) |

## Phases

| # | Phase | Effort | Status |
|---|-------|--------|--------|
| 1 | [Môi trường QA và baseline](./phase-01-moi-truong-qa-va-baseline.md) | 2.5h | Pending (bước 1 đã xong) |
| 2 | [Integration test backend thật (flow Như + Quân)](./phase-02-integration-test-backend-that.md) | 5h | Pending |
| 3 | [E2E giao diện, script SV3 và diễn tập demo](./phase-03-e2e-giao-dien-scripts-va-dien-tap-demo.md) | 4h | Pending |
| 4 | [Độ bền và lỗi biên](./phase-04-do-ben-va-loi-bien.md) | 3h | Pending |
| 5 | [Sửa lỗi theo chủ sở hữu và đưa develop lên main](./phase-05-sua-loi-theo-chu-so-huu.md) | 6h | Pending |
| 6 | [Deploy miễn phí](./phase-06-deploy-mien-phi.md) | 4h | Pending |

Thứ tự: 1 → 2 → (3 và 4 làm song song được, khác môi trường) → 5 → 6. Phase 2–4 **chỉ đo và ghi
bằng chứng**, không sửa code sản phẩm — sửa tập trung ở Phase 5 để test đỏ còn làm bằng chứng.

## Cách chạy với `/ak-debug`

```
/ak-debug plans/261025-1501-kiem-thu-on-dinh-toan-he-thong-va-deploy/plan.md — làm Phase 1
```
Mỗi phase có mục "Scout pass trước khi làm" — chạy trước, vì code có thể đã đổi.
Phase 5 dùng `/ak-fix` hoặc `/ak-cook`; Phase 6 dùng `/ak-cook` (hoặc `/ak-deploy`).

## Success Criteria

- [ ] Mọi giả thuyết G1–G28 có kết luận đúng/sai kèm bằng chứng (lệnh + output) trong `reports/`.
- [ ] Integration test thật xanh cho flow SV1 + SV2; `dotnet test` mặc định vẫn chạy không cần Docker.
- [ ] Mọi dòng Critical của E2E giao diện pass; script SV3 (seed, seed Redis, benchmark) chạy đúng.
- [ ] 3 bước demo theo đề chạy trơn 2 lượt liên tiếp; Redis demo có 20–50 key với TTL khác nhau.
- [ ] Redis chết: vẫn đọc được bài từ MongoDB, thao tác cần phiên trả 503 rõ ràng.
- [ ] PR `develop → main` đã merge; lỗi không được sửa đã gửi chủ file kèm bước tái hiện.
- [ ] Bản deploy qua smoke test production (đăng nhập, MISS→HIT, sửa bài xóa cache, F5 trang con).

## Validation Log

### Session 1 — 25/10/2026
- Sửa file người khác → **B** (xin phép nhóm rồi sửa lỗi chặn demo/barem).
- Lỗi Redis sập → sửa ngay, không hoãn sau hạn nộp.
- Deploy → sau khi kiểm thử toàn bộ xong; MongoDB cho deploy → Atlas M0 (512 MB, dữ liệu hiện ~78.5 MB).
- Cổng 27017 → được nhường khi cần.
- Nhánh → tạo `develop`, xong hết mới đưa lên `main`.

### Verification Results
- Claims checked: 18 (file:line trong báo cáo G1–G28, lệnh script, cổng, volume)
- Verified: 18 | Failed: 0 | Unverified: 2 (phiên bản `Microsoft.AspNetCore.Mvc.Testing` hợp với test `net10.0` → spike Phase 2 bước 1; Vite chạy với file config ngoài thư mục project → spike Phase 1 bước 5)
- Tier: Full (6 phase)

## Red Team Review

### Session — 25/10/2026 (tự rà soát theo 4 lăng kính, không tách reviewer riêng)

| # | Phát hiện | Mức | Xử lý | Áp vào |
|---|---|---|---|---|
| 1 | Redis QA mặc định có RDB → `docker restart` không làm mất dữ liệu, kịch bản G13 sẽ "pass giả" | High | Accept: chạy Redis QA với `--save "" --appendonly no` | Phase 1, 4 |
| 2 | Biến môi trường của factory là của cả tiến trình → hai collection xUnit chạy song song sẽ ghi đè nhau | High | Accept: một collection duy nhất, factory DB rỗng cho G16 tạo tuần tự | Phase 2 |
| 3 | Middleware 503 đăng ký sau `UseSessionAuth` sẽ không bắt được lỗi Redis trong middleware phiên | High | Accept: đăng ký ngay sau `UseCors()` | Phase 5 |
| 4 | Partial unique index "chỉ 1 admin" sẽ hỏng vì DB demo đã có 2 admin | High | Accept: dùng document `meta.bootstrapAdmin` | Phase 5 |
| 5 | Benchmark trỏ nhầm Redis demo sẽ `DEL` key demo | Medium | Accept: lệnh benchmark ghi rõ `--redis redis://localhost:6380/0` | Phase 3 |
| 6 | `force-recreate` container Mongo có thể gắn nhầm volume | Medium | Accept: đã xác nhận named volume `nosql-newscachesession_mongo_data` + sao lưu trước | Phase 3 |
| 7 | Chép `users` lên Atlas sẽ mang hash mật khẩu và tài khoản demo lên mạng | Medium | Accept: chỉ chép `posts` + `categories`, đăng ký admin ngay sau deploy | Phase 6 |

### Whole-Plan Consistency Sweep
Đã rà lại `plan.md` và 6 phase sau khi áp các mục trên: không còn nhắc "sau hạn nộp", cổng QA
thống nhất (27019/6380/5135/3001), nhánh thống nhất `develop`, phương án B thống nhất ở Phase 3/5/6.
Không còn mâu thuẫn.
