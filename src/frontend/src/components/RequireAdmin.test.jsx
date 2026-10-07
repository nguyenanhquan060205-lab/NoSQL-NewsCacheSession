import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/AuthContext';
import RequireAdmin from './RequireAdmin';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

function LoginProbe() {
  const location = useLocation();
  return <p>Đăng nhập từ {location.state?.from?.pathname || 'không rõ'}</p>;
}

function renderGuard() {
  return render(
    <MemoryRouter initialEntries={['/admin/posts']}>
      <Routes>
        <Route element={<RequireAdmin />}>
          <Route path="/admin/posts" element={<h1>Quản trị bài viết</h1>} />
        </Route>
        <Route path="/login" element={<LoginProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RequireAdmin', () => {
  beforeEach(() => {
    useAuth.mockReset();
  });

  it('không render nội dung trong lúc kiểm tra phiên', () => {
    useAuth.mockReturnValue({ status: 'loading', user: null, refresh: vi.fn() });
    renderGuard();

    expect(screen.getByRole('status')).toHaveTextContent('Đang kiểm tra quyền quản trị');
    expect(screen.queryByRole('heading', { name: 'Quản trị bài viết' })).not.toBeInTheDocument();
  });

  it('chuyển 401 về login và giữ đường dẫn quay lại', async () => {
    useAuth.mockReturnValue({ status: 'unauthenticated', user: null, refresh: vi.fn() });
    renderGuard();

    expect(await screen.findByText('Đăng nhập từ /admin/posts')).toBeInTheDocument();
  });

  it('hiện màn hình không đủ quyền cho user thường', async () => {
    useAuth.mockReturnValue({ status: 'authenticated', user: { role: 'user' }, refresh: vi.fn() });
    renderGuard();

    expect(await screen.findByRole('heading', { name: 'Bạn không có quyền truy cập' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Quản trị bài viết' })).not.toBeInTheDocument();
  });

  it('hiện lỗi mạng và gọi refresh khi thử lại', async () => {
    const user = userEvent.setup();
    const refresh = vi.fn();
    useAuth.mockReturnValue({ status: 'error', user: null, error: 'API tạm thời gián đoạn', refresh });
    renderGuard();

    expect(await screen.findByRole('alert')).toHaveTextContent('API tạm thời gián đoạn');
    expect(refresh).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: 'Thử kiểm tra lại' }));
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it('chờ revalidate route xong mới render outlet cho admin', async () => {
    let resolveRefresh;
    const refresh = vi.fn(() => new Promise((resolve) => { resolveRefresh = resolve; }));
    useAuth.mockReturnValue({ status: 'authenticated', user: { role: 'admin' }, refresh });
    renderGuard();

    expect(screen.queryByRole('heading', { name: 'Quản trị bài viết' })).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Đang kiểm tra quyền quản trị');

    resolveRefresh();

    expect(await screen.findByRole('heading', { name: 'Quản trị bài viết' })).toBeInTheDocument();
  });
});
