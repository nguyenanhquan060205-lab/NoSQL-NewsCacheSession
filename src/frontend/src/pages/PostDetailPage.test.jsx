import { StrictMode } from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { postsApi } from '../services/api';
import PostDetailPage from './PostDetailPage';

vi.mock('../services/api', () => ({ postsApi: { getById: vi.fn(), incrementView: vi.fn() } }));

function response(id = 'a', status = 'MISS', durationMs = 25.4) {
  return {
    data: { id, title: `Bài viết ${id}`, content: 'Nội dung bài viết', createdAt: '2026-10-08T00:00:00Z', views: 0 },
    cacheInfo: { status, durationMs },
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  // Cleanup vẫn có thể reject promise chưa được dùng nếu assertion trước đó thất bại.
  promise.catch(() => {});
  return { promise, resolve, reject };
}

function renderPage(strict = false) {
  const page = (
    <MemoryRouter initialEntries={['/posts/a']}>
      <Link to="/posts/a">Đi bài A</Link>
      <Link to="/posts/b">Đi bài B</Link>
      <Routes><Route path="/posts/:id" element={<PostDetailPage />} /></Routes>
    </MemoryRouter>
  );
  return render(strict ? <StrictMode>{page}</StrictMode> : page);
}

describe('PostDetailPage hồi quy và badge cache', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    postsApi.getById.mockResolvedValue(response());
    postsApi.incrementView.mockResolvedValue({ data: { views: 1 } });
  });

  it('đọc bài theo id và cập nhật lượt xem', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Bài viết a' })).toBeInTheDocument();
    expect(screen.getByText('Nội dung bài viết')).toBeInTheDocument();
    expect(postsApi.getById).toHaveBeenCalledWith('a');
    await waitFor(() => expect(screen.getByText('1 lượt xem')).toBeInTheDocument());
    expect(postsApi.incrementView).toHaveBeenCalledTimes(1);
  });

  it('gom GET khi StrictMode chạy lại effect và chỉ tăng view một lần', async () => {
    const request = deferred();
    postsApi.getById.mockReturnValue(request.promise);
    renderPage(true);
    expect(screen.getByRole('status', { name: 'Đang tải bài viết' })).toBeInTheDocument();
    expect(postsApi.getById).toHaveBeenCalledTimes(1);
    await act(async () => request.resolve(response()));
    expect(postsApi.incrementView).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('heading', { name: 'Bài viết a' })).toBeInTheDocument();
  });

  it('lỗi GET không tăng view và có thể thử lại', async () => {
    const user = userEvent.setup();
    postsApi.getById.mockRejectedValueOnce({ response: { status: 404, data: { message: 'Bài không tồn tại' } } });
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Bài không tồn tại');
    expect(postsApi.incrementView).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }));
    expect(await screen.findByRole('heading', { name: 'Bài viết a' })).toBeInTheDocument();
    expect(postsApi.getById).toHaveBeenCalledTimes(2);
  });

  it('lỗi tăng view không chặn nội dung', async () => {
    postsApi.incrementView.mockRejectedValue(new Error('Lỗi view'));
    renderPage();
    expect(await screen.findByText(/Lượt xem chưa được cập nhật/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Bài viết a' })).toBeInTheDocument();
  });

  it.each(['HIT', 'MISS', 'UNKNOWN'])('hiện badge %s theo metadata GET', async (status) => {
    postsApi.getById.mockResolvedValue(response('a', status));
    renderPage();
    expect(await screen.findByText(`CACHE ${status}`)).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 25,4 ms')).toBeInTheDocument();
  });

  it('metadata thiếu vẫn đọc bài và hiện UNKNOWN', async () => {
    const payload = response();
    delete payload.cacheInfo;
    postsApi.getById.mockResolvedValue(payload);
    renderPage();
    expect(await screen.findByText('CACHE UNKNOWN')).toBeInTheDocument();
    expect(screen.getByText('Chưa đo được thời gian')).toBeInTheDocument();
  });

  it('view pending hoặc lỗi không đổi badge/thời gian GET', async () => {
    const view = deferred();
    postsApi.incrementView.mockReturnValue(view.promise);
    renderPage();
    try {
      expect(await screen.findByText('CACHE MISS')).toBeInTheDocument();
      expect(screen.getByText('Phản hồi GET: 25,4 ms')).toBeInTheDocument();
    } finally {
      await act(async () => view.reject(new Error('Lỗi view')));
    }
    expect(screen.getByText('CACHE MISS')).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 25,4 ms')).toBeInTheDocument();
  });

  it('StrictMode giữ metadata của một GET thật', async () => {
    renderPage(true);
    expect(await screen.findByText('CACHE MISS')).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 25,4 ms')).toBeInTheDocument();
    expect(postsApi.getById).toHaveBeenCalledTimes(1);
    expect(postsApi.incrementView).toHaveBeenCalledTimes(1);
  });

  it.each(['resolve', 'reject'])('GET A %s muộn không ghi đè bài/badge B', async (completion) => {
    const old = deferred();
    const user = userEvent.setup();
    postsApi.getById.mockReturnValueOnce(old.promise).mockResolvedValueOnce(response('b', 'HIT', 3));
    renderPage();
    try {
      await user.click(screen.getByRole('link', { name: 'Đi bài B' }));
      expect(await screen.findByRole('heading', { name: 'Bài viết b' })).toBeInTheDocument();
    } finally {
      await act(async () => {
        if (completion === 'resolve') old.resolve(response('a', 'MISS', 900));
        else old.reject(new Error('GET A lỗi'));
      });
    }
    expect(screen.getByText('CACHE HIT')).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 3,0 ms')).toBeInTheDocument();
    expect(screen.queryByText('Bài viết a')).not.toBeInTheDocument();
    expect(postsApi.incrementView).toHaveBeenCalledTimes(1);
    expect(postsApi.incrementView).toHaveBeenCalledWith('b');
  });

  it('chuyển bài ẩn badge cũ; lỗi và retry lấy metadata mới', async () => {
    const next = deferred();
    const user = userEvent.setup();
    postsApi.getById.mockResolvedValueOnce(response()).mockReturnValueOnce(next.promise)
      .mockResolvedValueOnce(response('b', 'HIT', 5));
    renderPage();
    try {
      expect(await screen.findByText('CACHE MISS')).toBeInTheDocument();
      await user.click(screen.getByRole('link', { name: 'Đi bài B' }));
      expect(screen.queryByText('CACHE MISS')).not.toBeInTheDocument();
    } finally {
      await act(async () => next.reject(new Error('Lỗi mạng')));
    }
    expect(screen.queryByText(/CACHE (HIT|MISS|UNKNOWN)/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }));
    expect(await screen.findByText('CACHE HIT')).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 5,0 ms')).toBeInTheDocument();
    expect(postsApi.getById).toHaveBeenCalledTimes(3);
  });

  it('view của bài cũ hoàn tất không đổi metadata/lượt xem bài mới', async () => {
    const oldView = deferred();
    const user = userEvent.setup();
    postsApi.getById.mockResolvedValueOnce(response()).mockResolvedValueOnce(response('b', 'HIT', 2));
    postsApi.incrementView.mockReturnValueOnce(oldView.promise).mockResolvedValueOnce({ data: { views: 9 } });
    renderPage();
    try {
      await screen.findByRole('heading', { name: 'Bài viết a' });
      await user.click(screen.getByRole('link', { name: 'Đi bài B' }));
      await screen.findByRole('heading', { name: 'Bài viết b' });
    } finally {
      await act(async () => oldView.resolve({ data: { views: 100 } }));
    }
    expect(screen.getByText('9 lượt xem')).toBeInTheDocument();
    expect(screen.getByText('CACHE HIT')).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 2,0 ms')).toBeInTheDocument();
  });

  it('unmount bỏ qua GET muộn, vào lại tạo GET mới sau khi request cũ xong', async () => {
    const old = deferred();
    postsApi.getById.mockReturnValueOnce(old.promise).mockResolvedValueOnce(response('a', 'HIT', 1));
    const page = renderPage();
    page.unmount();
    await act(async () => old.resolve(response()));
    expect(postsApi.incrementView).not.toHaveBeenCalled();
    renderPage();
    expect(await screen.findByText('CACHE HIT')).toBeInTheDocument();
    expect(postsApi.getById).toHaveBeenCalledTimes(2);
  });
});
