# Quy Chuẩn Độ Dài File Mã Nguồn (LOC Limit & Code Modularity)

## 1. Giới Hạn Dòng Lệnh (LOC Rules)
- **Độ dài lý tưởng:** `150 – 250 LOC` / file.
- **Giới hạn cứng (Hard Limit):** Tuyệt đối **KHÔNG ĐƯỢC VƯỢT QUÁ 300 LOC** (Max 300 lines) cho mọi file code (`.tsx`, `.ts`, `.dart`, `.py`) trên toàn bộ dự án (**Web**, **Mobile Flutter**, **Backend Python**).

## 2. Nguyên Tắc Phân Tách Khi Chạm Ngưỡng (Single Responsibility)
- **Web (Next.js / React / TypeScript):**
  - Khi component chạm mốc 250–300 LOC:
    - Tách toàn bộ State, Effect, Handler phức tạp ra **Custom Hook** (`hooks/use...ts`).
    - Bóc tách các thành phần con (Sub-components, Modal, Wizard Steps, Table Row) ra thư mục con hoặc file riêng.
    - Chuyển Type/Interface và Constants dài sang file `types.ts` hoặc `constants.ts`.
- **Mobile (Flutter / Dart):**
  - Tuyệt đối không viết toàn bộ màn hình vào 1 file State duy nhất.
  - Tách các Widget con lồng ghép (Card, List Item, Header, Filter Bar,...) ra thư mục `widgets/` dưới dạng `StatelessWidget` hoặc `StatefulWidget` độc lập.
  - Tách Dialog, BottomSheet, và Menu ra file riêng.
  - Tách Business Logic (Bloc / Provider / Controller) ra khỏi UI Screen.
- **Backend (Python / FastAPI):**
  - Mỗi file Service hoặc Router chỉ giải quyết một miền nghiệp vụ (Domain) cụ thể.
  - Tách Schemas (Pydantic models) và Database Models ra thư mục riêng.

## 3. Các Trường Hợp Ngoại Lệ
- File mã nguồn do tool / framework tự động sinh (`*.g.dart`, `*.freezed.dart`).
- File schema database migration.
- File danh mục hằng số dữ liệu tĩnh tuyển sinh HUIT thuần JSON / data mapping.
