import { Link } from 'react-router-dom';

// TODO [SV3]: Implement thanh điều hướng
// - Logo/Brand link về trang chủ
// - Nếu chưa đăng nhập → nút "Đăng nhập"
// - Nếu đã đăng nhập → hiển thị Username + nút "Viết bài" + nút "Đăng xuất"
// - Gọi authApi.getMe() để kiểm tra session khi component mount

export default function Navbar() {
  return (
    <nav className="bg-white shadow-md px-6 py-4 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold text-blue-600">
        📰 NewsCacheSession
      </Link>
      <div className="flex items-center gap-4">
        {/* TODO [SV3]: Render login/logout buttons dựa trên session state */}
        <Link to="/login" className="text-gray-600 hover:text-blue-600">
          Đăng nhập
        </Link>
      </div>
    </nav>
  );
}
