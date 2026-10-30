# scripts/DocCheck — Bộ kiểm tra tính nhất quán tài liệu SRS

Thư mục chứa script kiểm tra tính đúng đắn và nhất quán của tài liệu đặc tả `docs/SRS.md`
với mã nguồn, cấu hình hệ thống, số đo hiệu năng, đề bài gốc và Jira tasks.

**Chủ sở hữu:** SV2 — Nguyễn Anh Quân (Advanced Query Specialist)

## Mục đích
- Đảm bảo tài liệu SRS phản ánh 100% sự thật từ mã nguồn và dữ liệu thực tế.
- Tự động phát hiện sai lệch (tên cookie, cổng kết nối, endpoint, versions, keyspace, latency...).
- Chạy kiểm thử tự động trước khi nghiệm thu hoặc demo bảo vệ.

## Lệnh chạy

1. Chạy toàn bộ 12 phép kiểm tra trên `docs/SRS.md`:
```bash
python3 scripts/DocCheck/check_srs.py
```

2. Chạy trên file SRS cụ thể hoặc chỉ định phép kiểm:
```bash
python3 scripts/DocCheck/check_srs.py --srs docs/SRS.md --only C1,C4,C6
```

3. Chạy bộ unit test của checker:
```bash
python3 -m unittest discover -s scripts/DocCheck -p 'test_*.py' -v
```

*Lưu ý: Checker yêu cầu Python 3.10+ và chỉ sử dụng thư viện chuẩn.*

