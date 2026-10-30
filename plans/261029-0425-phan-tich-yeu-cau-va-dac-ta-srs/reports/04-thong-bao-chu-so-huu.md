# Báo cáo thông báo cho chủ sở hữu tài liệu

**Gửi:** Hồ Ngọc Phương Như (SV1), Nguyễn Xuân Định (SV3) và Nhóm Đề tài 06  
**Người gửi:** Nguyễn Anh Quân (SV2 — Advanced Query Specialist)  
**Ngày:** 29/10/2026  
**Chủ đề:** Các điểm sai lệch và lạc hậu trong các tài liệu khác cần cập nhật sau khi hoàn thiện đặc tả SRS v3.0

---

Chào Như và Định,

Trong quá trình rà soát và kiểm chứng tự động toàn bộ mã nguồn hệ thống để xây dựng đặc tả **SRS v3.0** (`docs/SRS.md`) và bộ kiểm thử tài liệu `scripts/DocCheck/check_srs.py`, Quân đã phát hiện một số điểm lạc hậu/sai lệch trong các tài liệu do Như và Định quản lý (theo phân công tại `AGENTS.md` §4, Quân không tự ý sửa file của thành viên khác).

Dưới đây là danh sách chi tiết các mục cần cập nhật:

### 1. Gửi Như (SV1 — Data Architect & CRUD Lead)
*   **File:** `docs/checklist-barem.md` (dòng 22 và dòng 128)
    *   *Hiện trạng*: Vẫn ghi phần 4 là *"chưa có số đo, chưa có biểu đồ"*.
    *   *Thực tế*: Nhóm đã thực hiện đo kiểm hiệu năng chính thức ngày 25/10/2026, vẽ biểu đồ trực quan (`scripts/Benchmark/results/2026-10-25-chinh-thuc/charts/`) và có báo cáo đầy đủ tại `docs/bao-cao-kiem-thu-hieu-nang.md`.
    *   *Đề xuất*: Như cập nhật lại mục này trong checklist thành đã hoàn thành (Done) và dẫn link tới báo cáo hiệu năng.

### 2. Gửi Định (SV3 — Fullstack Integrator & DB Tester)
*   **File:** `docs/kich-ban-demo-va-do-hieu-nang.md` (dòng 368)
    *   *Hiện trạng*: Còn văn bản giữ chỗ *"Đo ngày __/__/2026 … 101 bài viết"*.
    *   *Thực tế*: Ngày đo chính thức là **25/10/2026**; CSDL demo thực tế có **10.251** bài viết (10.150 bài hoạt động), bản deploy có **10.000** bài viết hoạt động.
    *   *Đề xuất*: Định điền ngày đo chính thức và số lượng bài viết thực tế vào kịch bản để tránh bị thầy hỏi khi demo.
*   **Thư mục:** `scripts/SeedPosts/` và `scripts/Benchmark/`
    *   *Ghi chú*: Khi chạy unit test trên môi trường máy sạch, `test_plot.py` cần cài `matplotlib` (`pip install matplotlib`), và các script seed cần `pymongo` (`pip install pymongo`). Định nên bổ sung file `requirements.txt` vào các thư mục script để người khác dễ cài đặt.

### 3. Gửi Cả Nhóm (File dùng chung & Jira)
*   **File:** `AGENTS.md` (Mục 6: "Việc còn thiếu")
    *   *Hiện trạng*: Vẫn ghi *"SessionAuthMiddleware (đang là stub)"* và liệt kê 5 việc của SV2 "đang chờ ai làm".
    *   *Thực tế*: Toàn bộ 5 việc này (`SessionAuthMiddleware`, Cache-Aside `GetById`, `IncrementView` + Write-Behind worker, cache danh sách theo version, header `X-Cache`) đã được Quân hoàn thành 100% từ ngày 23/10/2026 và đã kiểm thử tự động xanh.
    *   *Đề xuất*: Nhóm họp thống nhất cập nhật lại Mục 6 trong `AGENTS.md`.
*   **File:** `docs/nosql-jira-tasks.csv`
    *   *Hiện trạng*: 11 ticket (SCRUM-33, 39–45, 47–49) vẫn mang trạng thái Idea hoặc In Progress trong khi mã nguồn và tài liệu tương ứng đều đã hoàn thành. Ngoài ra, Sprint 1 (23–24 Sep) và Sprint 2 (23–29 Sep) bị gối ngày.
    *   *Đề xuất*: Nhóm đồng bộ lại trạng thái Jira lên hệ thống Jira của trường nếu có đợt kiểm tra cuối kỳ.

---

Bản đặc tả **SRS v3.0** hiện đã được lưu tại `docs/SRS.md`, vượt qua 100% (12/12) phép kiểm tra tự động của `check_srs.py` và đã được đối chiếu thực nghiệm trên cả Docker local lẫn bản deploy Render/Vercel.

Thân ái,  
**Nguyễn Anh Quân (SV2)**

