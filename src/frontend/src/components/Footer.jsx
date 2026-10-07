import { Link } from 'react-router-dom';

const footerColumns = [
  {
    title: 'Tin tức',
    links: ['Mới nhất', 'Thời sự', 'Thế giới', 'Kinh doanh'],
  },
  {
    title: 'Đời sống',
    links: ['Sức khỏe', 'Giáo dục', 'Du lịch', 'Giải trí'],
  },
  {
    title: 'Công nghệ',
    links: ['Số hóa', 'AI', 'Dữ liệu', 'Khởi nghiệp'],
  },
];

export default function Footer() {
  return (
    <footer className="mt-12 border-t-4 border-red-700 bg-zinc-950 text-zinc-300">
      <h2 className="sr-only">Thông tin và điều hướng cuối trang</h2>

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-8 border-b border-zinc-800 py-10 sm:grid-cols-2 lg:grid-cols-[1.25fr_0.75fr_0.75fr_0.75fr] lg:py-12">
          <section>
            <Link to="/" className="inline-flex min-h-11 items-center" aria-label="NewsCache - Trang chủ">
              <span className="font-editorial text-2xl font-black tracking-[-0.05em] text-white">
                NEWS<span className="text-red-700">CACHE</span>
              </span>
            </Link>
            <p className="mt-3 max-w-sm text-sm leading-6 text-zinc-400">
              Trang tin tức trực tuyến thử nghiệm cơ chế Redis Cache-Aside để tăng tốc độ đọc bài và quản lý phiên đăng nhập.
            </p>
          </section>

          {footerColumns.map((column) => (
            <nav key={column.title} aria-label={column.title}>
              <h3 className="border-b border-zinc-800 pb-2 text-sm font-black uppercase tracking-[0.08em] text-white">
                {column.title}
              </h3>
              <ul className="mt-2 space-y-1">
                {column.links.map((link) => (
                  <li key={link}>
                    <a
                      href="/#tin-moi"
                      className="inline-flex min-h-9 items-center text-sm text-zinc-400 transition-colors hover:text-white"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="grid gap-8 border-b border-zinc-800 py-8 md:grid-cols-2 lg:grid-cols-[1fr_1fr_auto]">
          <section>
            <h3 className="text-sm font-black uppercase tracking-[0.08em] text-white">Thông tin dự án</h3>
            <div className="mt-3 space-y-1 text-sm leading-6 text-zinc-400">
              <p>Đề tài 06: Caching bài viết và quản lý phiên</p>
              <p>Nhóm thực hiện: 03 sinh viên</p>
              <p>Cơ sở dữ liệu: MongoDB · Bộ nhớ đệm: Redis</p>
            </div>
          </section>

          <section>
            <h3 className="text-sm font-black uppercase tracking-[0.08em] text-white">Liên hệ nhóm phát triển</h3>
            <div className="mt-3 space-y-1 text-sm leading-6 text-zinc-400">
              <p>Kho mã nguồn và tài liệu nằm trong dự án NewsCacheSession.</p>
              <p>Mọi dữ liệu hiển thị chỉ phục vụ mục đích học tập và kiểm thử.</p>
            </div>
          </section>

          <div className="md:col-span-2 lg:col-span-1 lg:text-right">
            <a
              href="#main-content"
              className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-zinc-700 px-4 text-sm font-bold text-zinc-200 transition-colors hover:border-red-500 hover:text-white"
            >
              Lên đầu trang
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="m18 15-6-6-6 6" />
              </svg>
            </a>
          </div>
        </div>

        <div className="flex flex-col gap-2 py-5 text-xs leading-5 text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} NewsCache. Bảo lưu nội dung thuộc phạm vi đồ án.</p>
          <p className="font-semibold text-zinc-400">Sản phẩm học tập · Không phải cơ quan báo chí</p>
        </div>
      </div>
    </footer>
  );
}
