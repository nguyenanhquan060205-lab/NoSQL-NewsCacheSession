import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/useAuth';
import { categoriesApi, postsApi } from '../services/api';
import AdminPostsPage from './AdminPostsPage';

vi.mock('../context/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../services/api', () => ({
  postsApi: { getAll: vi.fn(), delete: vi.fn() },
  categoriesApi: { getAll: vi.fn() },
}));

const samplePost = {
  id: 'post-1',
  title: 'Bài viết thử nghiệm',
  categoryId: 'cat-1',
  views: 42,
  updatedAt: '2026-10-07T08:00:00Z',
};

function renderPage(initialEntry = '/admin/posts') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/admin/posts" element={<AdminPostsPage />} />
        <Route path="/login" element={<p>Trang đăng nhập</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminPostsPage', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ clearAuth: vi.fn() });
    categoriesApi.getAll.mockResolvedValue({ data: [{ id: 'cat-1', name: 'Công nghệ' }] });
    postsApi.getAll.mockResolvedValue({
      data: { items: [samplePost], page: 1, pageSize: 12, totalItems: 1, totalPages: 1 },
    });
    postsApi.delete.mockResolvedValue({ status: 204 });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  it('tải 12 bài mỗi trang và render dữ liệu/category', async () => {
    renderPage();

    expect(screen.getByRole('status')).toHaveTextContent('Đang tải danh sách bài viết');
    expect(await screen.findByRole('heading', { name: 'Quản trị bài viết' })).toBeInTheDocument();
    expect(postsApi.getAll).toHaveBeenCalledWith(1, 12);
    expect(screen.getAllByText('Bài viết thử nghiệm').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Công nghệ').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/42 lượt xem/).length).toBeGreaterThan(0);
  });

  it('vẫn render bài viết khi categories lỗi', async () => {
    categoriesApi.getAll.mockRejectedValue(new Error('category down'));
    renderPage();

    expect(await screen.findByText('Bài viết thử nghiệm')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'Cảnh báo chuyên mục' })).toBeInTheDocument();
    expect(screen.getAllByText('Không xác định').length).toBeGreaterThan(0);
  });

  it('hiện trạng thái rỗng khi trang không có bài viết', async () => {
    postsApi.getAll.mockResolvedValue({
      data: { items: [], page: 1, pageSize: 12, totalItems: 0, totalPages: 0 },
    });
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Chưa có bài viết nào' })).toBeInTheDocument();
  });

  it('hiện lỗi tải danh sách và cho phép thử lại', async () => {
    const user = userEvent.setup();
    postsApi.getAll
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce({ data: { items: [samplePost], page: 1, pageSize: 12, totalItems: 1, totalPages: 1 } });
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải danh sách bài viết');
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }));
    expect(await screen.findByText('Bài viết thử nghiệm')).toBeInTheDocument();
  });

  it('không xóa khi người dùng hủy xác nhận', async () => {
    const user = userEvent.setup();
    window.confirm.mockReturnValue(false);
    renderPage();

    const deleteButtons = await screen.findAllByRole('button', { name: 'Xóa Bài viết thử nghiệm' });
    await user.click(deleteButtons[0]);
    expect(postsApi.delete).not.toHaveBeenCalled();
  });

  it('xóa đúng một lần và tải lại danh sách', async () => {
    const user = userEvent.setup();
    renderPage();

    const table = await screen.findByRole('table');
    await user.click(within(table).getByRole('button', { name: 'Xóa Bài viết thử nghiệm' }));

    await waitFor(() => expect(postsApi.delete).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(postsApi.getAll).toHaveBeenCalledTimes(2));
  });

  it('lùi một trang khi xóa bài cuối cùng của trang hiện tại', async () => {
    const user = userEvent.setup();
    postsApi.getAll
      .mockResolvedValueOnce({ data: { items: [samplePost], page: 2, pageSize: 12, totalItems: 13, totalPages: 2 } })
      .mockResolvedValueOnce({ data: { items: [], page: 1, pageSize: 12, totalItems: 12, totalPages: 1 } });
    renderPage('/admin/posts?page=2');

    const table = await screen.findByRole('table');
    await user.click(within(table).getByRole('button', { name: 'Xóa Bài viết thử nghiệm' }));

    await waitFor(() => expect(postsApi.getAll).toHaveBeenNthCalledWith(2, 1, 12));
    expect(await screen.findByRole('heading', { name: 'Chưa có bài viết nào' })).toBeInTheDocument();
  });

  it('xóa không thành công thì giữ bài và hiện lỗi API', async () => {
    const user = userEvent.setup();
    postsApi.delete.mockRejectedValue({ response: { status: 403, data: { message: 'Không đủ quyền xóa bài.' } } });
    renderPage();

    const table = await screen.findByRole('table');
    await user.click(within(table).getByRole('button', { name: 'Xóa Bài viết thử nghiệm' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Không đủ quyền xóa bài.');
    expect(screen.getByText('Bài viết thử nghiệm')).toBeInTheDocument();
  });

  it('xóa gặp 401 thì xóa auth state và chuyển về login', async () => {
    const user = userEvent.setup();
    const clearAuth = vi.fn();
    useAuth.mockReturnValue({ clearAuth });
    postsApi.delete.mockRejectedValue({ response: { status: 401 } });
    renderPage();

    const table = await screen.findByRole('table');
    await user.click(within(table).getByRole('button', { name: 'Xóa Bài viết thử nghiệm' }));

    expect(await screen.findByText('Trang đăng nhập')).toBeInTheDocument();
    expect(clearAuth).toHaveBeenCalledTimes(1);
  });

  it('đưa URL vượt biên về trang cuối hợp lệ', async () => {
    postsApi.getAll
      .mockResolvedValueOnce({ data: { items: [], page: 999, pageSize: 12, totalItems: 13, totalPages: 2 } })
      .mockResolvedValueOnce({ data: { items: [samplePost], page: 2, pageSize: 12, totalItems: 13, totalPages: 2 } });

    renderPage('/admin/posts?page=999');

    await waitFor(() => expect(postsApi.getAll).toHaveBeenNthCalledWith(2, 2, 12));
    expect(await screen.findByText('Bài viết thử nghiệm')).toBeInTheDocument();
  });
});
