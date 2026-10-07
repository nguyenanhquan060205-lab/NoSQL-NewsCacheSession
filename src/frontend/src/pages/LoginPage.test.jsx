import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/useAuth';
import { authApi } from '../services/api';
import LoginPage from './LoginPage';

vi.mock('../context/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../services/api', () => ({ authApi: { login: vi.fn(), register: vi.fn() } }));

function Destination() {
  const location = useLocation();
  return <h1>Đang ở {location.pathname}</h1>;
}

function renderLogin(initialEntry = '/login') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Destination />} />
        <Route path="/admin/posts" element={<Destination />} />
        <Route path="/posts/new" element={<Destination />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  const refresh = vi.fn();

  beforeEach(() => {
    authApi.login.mockReset();
    authApi.register.mockReset();
    refresh.mockReset();
    refresh.mockResolvedValue({ role: 'admin' });
    useAuth.mockReturnValue({ refresh });
  });

  it('đăng nhập bằng username đã trim rồi quay về route được yêu cầu', async () => {
    const user = userEvent.setup();
    authApi.login.mockResolvedValue({ data: { role: 'admin' } });
    renderLogin({ pathname: '/login', state: { from: { pathname: '/admin/posts', search: '?page=2', hash: '#list' } } });

    await user.type(screen.getByLabelText('Tên đăng nhập'), ' admin1 ');
    await user.type(screen.getByLabelText('Mật khẩu'), 'secret1');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    await waitFor(() => expect(authApi.login).toHaveBeenCalledWith('admin1', 'secret1'));
    expect(refresh).toHaveBeenCalledWith({ force: true });
    expect(await screen.findByRole('heading', { name: 'Đang ở /admin/posts' })).toBeInTheDocument();
  });

  it('đăng nhập bình thường thì về trang chủ', async () => {
    const user = userEvent.setup();
    authApi.login.mockResolvedValue({ data: { role: 'user' } });
    renderLogin();

    await user.type(screen.getByLabelText('Tên đăng nhập'), 'reader1');
    await user.type(screen.getByLabelText('Mật khẩu'), 'secret1');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    expect(await screen.findByRole('heading', { name: 'Đang ở /' })).toBeInTheDocument();
  });

  it('đăng ký xong trở về đăng nhập, giữ username và yêu cầu đăng nhập riêng', async () => {
    const user = userEvent.setup();
    authApi.register.mockResolvedValue({ status: 201 });
    renderLogin();

    await user.click(screen.getByRole('button', { name: 'Chưa có tài khoản? Đăng ký' }));
    await user.type(screen.getByLabelText('Tên đăng nhập'), ' newuser ');
    await user.type(screen.getByLabelText('Mật khẩu'), 'secret1');
    await user.click(screen.getByRole('button', { name: 'Tạo tài khoản' }));

    expect(authApi.register).toHaveBeenCalledWith('newuser', 'secret1');
    expect(await screen.findByRole('status')).toHaveTextContent('Tài khoản đã tạo. Đăng nhập để tiếp tục.');
    expect(screen.getByLabelText('Tên đăng nhập')).toHaveValue('newuser');
    expect(screen.getByLabelText('Mật khẩu')).toHaveValue('');
    expect(authApi.login).not.toHaveBeenCalled();
  });

  it('hiện lỗi đăng nhập API và giữ nguyên thông tin đã nhập', async () => {
    const user = userEvent.setup();
    authApi.login.mockRejectedValue({ response: { status: 401, data: { message: 'Sai username hoặc password' } } });
    renderLogin();

    await user.type(screen.getByLabelText('Tên đăng nhập'), 'reader1');
    await user.type(screen.getByLabelText('Mật khẩu'), 'wrongpass');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Sai username hoặc password');
    expect(screen.getByLabelText('Tên đăng nhập')).toHaveValue('reader1');
    expect(screen.getByLabelText('Mật khẩu')).toHaveValue('wrongpass');
  });

  it('không điều hướng ra ngoài ứng dụng từ location state', async () => {
    const user = userEvent.setup();
    authApi.login.mockResolvedValue({ data: { role: 'user' } });
    renderLogin({ pathname: '/login', state: { from: { pathname: '//evil.example' } } });

    await user.type(screen.getByLabelText('Tên đăng nhập'), 'reader1');
    await user.type(screen.getByLabelText('Mật khẩu'), 'secret1');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    expect(await screen.findByRole('heading', { name: 'Đang ở /' })).toBeInTheDocument();
  });
});
