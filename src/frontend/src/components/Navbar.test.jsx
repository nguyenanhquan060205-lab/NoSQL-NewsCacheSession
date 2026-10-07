import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/useAuth';
import { authApi, categoriesApi } from '../services/api';
import Navbar from './Navbar';

vi.mock('../context/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../services/api', () => ({
  authApi: { logout: vi.fn() },
  categoriesApi: { getAll: vi.fn() },
}));

describe('Navbar', () => {
  beforeEach(() => {
    authApi.logout.mockReset();
    authApi.logout.mockResolvedValue({ status: 200 });
    categoriesApi.getAll.mockResolvedValue({ data: [] });
  });

  it('chỉ hiện link quản trị cho admin', () => {
    useAuth.mockReturnValue({ status: 'authenticated', user: { role: 'admin' } });
    const { unmount } = render(<MemoryRouter><Navbar /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Quản trị bài viết' })).toHaveAttribute('href', '/admin/posts');
    unmount();

    useAuth.mockReturnValue({ status: 'authenticated', user: { role: 'user' } });
    render(<MemoryRouter><Navbar /></MemoryRouter>);
    expect(screen.queryByRole('link', { name: 'Quản trị bài viết' })).not.toBeInTheDocument();
  });

  it('đăng xuất qua API, xóa auth state và điều hướng về trang chủ', async () => {
    const user = userEvent.setup();
    const clearAuth = vi.fn();
    useAuth.mockReturnValue({ status: 'authenticated', user: { username: 'reader1', role: 'user' }, clearAuth });
    render(<MemoryRouter><Navbar /></MemoryRouter>);

    await user.click(screen.getByRole('button', { name: 'Đăng xuất' }));

    await waitFor(() => expect(authApi.logout).toHaveBeenCalledTimes(1));
    expect(clearAuth).toHaveBeenCalledTimes(1);
  });

  it('giữ phiên và báo lỗi nếu API đăng xuất thất bại', async () => {
    const user = userEvent.setup();
    const clearAuth = vi.fn();
    authApi.logout.mockRejectedValue({ response: { status: 500, data: { message: 'Không thể đăng xuất lúc này.' } } });
    useAuth.mockReturnValue({ status: 'authenticated', user: { username: 'reader1', role: 'user' }, clearAuth });
    render(<MemoryRouter><Navbar /></MemoryRouter>);

    await user.click(screen.getByRole('button', { name: 'Đăng xuất' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể đăng xuất lúc này.');
    expect(clearAuth).not.toHaveBeenCalled();
  });
});
