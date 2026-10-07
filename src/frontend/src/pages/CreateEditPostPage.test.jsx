import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/useAuth';
import { categoriesApi, postsApi } from '../services/api';
import CreateEditPostPage from './CreateEditPostPage';

vi.mock('../context/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../services/api', () => ({
  postsApi: { getById: vi.fn(), create: vi.fn(), update: vi.fn() },
  categoriesApi: { getAll: vi.fn() },
}));

function renderForm(route = '/posts/new') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/posts/new" element={<CreateEditPostPage />} />
        <Route path="/posts/:id/edit" element={<CreateEditPostPage />} />
        <Route path="/posts/:id" element={<p>Đã đến trang chi tiết</p>} />
        <Route path="/login" element={<p>Trang đăng nhập</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CreateEditPostPage', () => {
  const clearAuth = vi.fn();

  beforeEach(() => {
    window.sessionStorage.clear();
    clearAuth.mockReset();
    useAuth.mockReturnValue({ clearAuth });
    categoriesApi.getAll.mockResolvedValue({ data: [{ id: 'cat-1', name: 'Công nghệ' }] });
    postsApi.create.mockResolvedValue({ data: { id: 'new-post' } });
    postsApi.update.mockResolvedValue({ data: { id: 'post-1' } });
    postsApi.getById.mockResolvedValue({
      data: { id: 'post-1', title: 'Tiêu đề cũ', content: 'Nội dung cũ', imageUrl: null, categoryId: 'cat-1' },
    });
  });

  it('create mode không tải post và gửi payload đã chuẩn hóa', async () => {
    const user = userEvent.setup();
    renderForm();

    expect(await screen.findByRole('option', { name: 'Công nghệ' })).toBeInTheDocument();
    expect(postsApi.getById).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText('Tiêu đề'), '  Bài mới  ');
    await user.type(screen.getByLabelText('Nội dung'), '  Nội dung mới  ');
    await user.click(screen.getByRole('button', { name: 'Đăng bài' }));

    await waitFor(() => expect(postsApi.create).toHaveBeenCalledWith({
      title: 'Bài mới',
      content: 'Nội dung mới',
      imageUrl: null,
      categoryId: null,
    }));
    expect(await screen.findByText('Đã đến trang chi tiết')).toBeInTheDocument();
  });

  it('chặn dữ liệu chỉ chứa khoảng trắng', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('Tiêu đề'), '   ');
    await user.type(screen.getByLabelText('Nội dung'), '   ');
    await user.click(screen.getByRole('button', { name: 'Đăng bài' }));

    expect(await screen.findByText('Tiêu đề không được để trống.')).toBeInTheDocument();
    expect(screen.getByText('Nội dung không được để trống.')).toBeInTheDocument();
    expect(postsApi.create).not.toHaveBeenCalled();
  });

  it('chặn URL hình ảnh không hợp lệ', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('Tiêu đề'), 'Bài mới');
    await user.type(screen.getByLabelText('Nội dung'), 'Nội dung mới');
    await user.type(screen.getByLabelText('URL hình ảnh'), 'khong-phai-url');
    await user.click(screen.getByRole('button', { name: 'Đăng bài' }));

    expect(await screen.findByText('URL hình ảnh phải bắt đầu bằng http:// hoặc https://.')).toBeInTheDocument();
    expect(postsApi.create).not.toHaveBeenCalled();
  });

  it('khóa hai submit xảy ra cùng lượt event', async () => {
    let resolveCreate;
    postsApi.create.mockReturnValue(new Promise((resolve) => { resolveCreate = resolve; }));
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('Tiêu đề'), 'Bài mới');
    await user.type(screen.getByLabelText('Nội dung'), 'Nội dung mới');
    const form = screen.getByRole('button', { name: 'Đăng bài' }).closest('form');
    fireEvent.submit(form);
    fireEvent.submit(form);

    expect(postsApi.create).toHaveBeenCalledTimes(1);
    resolveCreate({ data: { id: 'new-post' } });
    expect(await screen.findByText('Đã đến trang chi tiết')).toBeInTheDocument();
  });

  it('edit mode prefill và cập nhật đúng bài', async () => {
    const user = userEvent.setup();
    renderForm('/posts/post-1/edit');

    expect(await screen.findByDisplayValue('Tiêu đề cũ')).toBeInTheDocument();
    expect(screen.getByLabelText('Chuyên mục')).toHaveValue('cat-1');

    await user.clear(screen.getByLabelText('Tiêu đề'));
    await user.type(screen.getByLabelText('Tiêu đề'), 'Tiêu đề mới');
    await user.click(screen.getByRole('button', { name: 'Cập nhật bài viết' }));

    await waitFor(() => expect(postsApi.update).toHaveBeenCalledWith('post-1', {
      title: 'Tiêu đề mới',
      content: 'Nội dung cũ',
      imageUrl: null,
      categoryId: 'cat-1',
    }));
    expect(await screen.findByText('Đã đến trang chi tiết')).toBeInTheDocument();
  });

  it('hiện lỗi từng trường từ ValidationProblemDetails và giữ form', async () => {
    const user = userEvent.setup();
    postsApi.create.mockRejectedValue({
      response: {
        status: 400,
        data: {
          title: 'One or more validation errors occurred.',
          errors: { Title: ['Tiêu đề đã tồn tại.'] },
        },
      },
    });
    renderForm();

    await user.type(screen.getByLabelText('Tiêu đề'), 'Tiêu đề bị từ chối');
    await user.type(screen.getByLabelText('Nội dung'), 'Nội dung còn được giữ');
    await user.click(screen.getByRole('button', { name: 'Đăng bài' }));

    expect(await screen.findByText('Tiêu đề đã tồn tại.', { selector: '#post-title-error' })).toBeInTheDocument();
    expect(screen.getByLabelText('Tiêu đề')).toHaveValue('Tiêu đề bị từ chối');
    expect(screen.getByLabelText('Nội dung')).toHaveValue('Nội dung còn được giữ');
  });

  it('vẫn prefill bài viết khi tải chuyên mục thất bại', async () => {
    categoriesApi.getAll.mockRejectedValue(new Error('category down'));
    renderForm('/posts/post-1/edit');

    expect(await screen.findByDisplayValue('Tiêu đề cũ')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'Cảnh báo chuyên mục' })).toBeInTheDocument();
  });

  it('giữ bản nháp và chuyển login khi phiên hết hạn lúc tạo bài', async () => {
    const user = userEvent.setup();
    postsApi.create.mockRejectedValue({ response: { status: 401 } });
    renderForm();

    await user.type(screen.getByLabelText('Tiêu đề'), 'Bài đang viết');
    await user.type(screen.getByLabelText('Nội dung'), 'Nội dung cần được giữ lại');
    await user.click(screen.getByRole('button', { name: 'Đăng bài' }));

    expect(await screen.findByText('Trang đăng nhập')).toBeInTheDocument();
    expect(clearAuth).toHaveBeenCalledTimes(1);
    expect(JSON.parse(window.sessionStorage.getItem('scrum29:post-draft:create'))).toMatchObject({
      title: 'Bài đang viết',
      content: 'Nội dung cần được giữ lại',
    });
  });
});
