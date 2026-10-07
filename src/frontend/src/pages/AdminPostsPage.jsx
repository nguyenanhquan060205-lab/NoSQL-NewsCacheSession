import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { categoriesApi, postsApi } from '../services/api';
import { getApiMessage, getApiStatus } from '../utils/apiError';

const PAGE_SIZE = 12;

function parseAdminPage(value) {
  if (!value || !/^\d+$/.test(value)) return 1;
  const page = Number(value);
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Chưa cập nhật'
    : date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function LoadingRows() {
  return (
    <div role="status" aria-live="polite" className="rounded-xl border border-zinc-200 bg-white px-5 py-12 text-center">
      <div className="mx-auto size-9 animate-spin rounded-full border-4 border-zinc-200 border-t-red-700" aria-hidden="true" />
      <p className="mt-4 text-sm font-bold text-zinc-600">Đang tải danh sách bài viết...</p>
    </div>
  );
}

export default function AdminPostsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { clearAuth } = useAuth();
  const [posts, setPosts] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loadedRequestKey, setLoadedRequestKey] = useState(null);
  const [error, setError] = useState('');
  const [categories, setCategories] = useState([]);
  const [categoryError, setCategoryError] = useState('');
  const [categoryVersion, setCategoryVersion] = useState(0);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [deletingIds, setDeletingIds] = useState(() => new Set());
  const [deleteError, setDeleteError] = useState('');
  const requestGenerationRef = useRef(0);
  const deleteInFlightRef = useRef(new Set());
  const rawPage = searchParams.get('page');
  const page = parseAdminPage(rawPage);
  const requestKey = `${page}:${reloadVersion}`;
  const loading = loadedRequestKey !== requestKey;

  const replacePage = useCallback((nextPage) => {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete('page');
    else next.set('page', String(nextPage));
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (rawPage && rawPage !== String(page)) replacePage(page);
  }, [page, rawPage, replacePage]);

  useEffect(() => {
    const generation = ++requestGenerationRef.current;
    let active = true;

    postsApi.getAll(page, PAGE_SIZE)
      .then((response) => {
        if (!active || generation !== requestGenerationRef.current) return;
        const payload = response.data || {};
        const nextTotalPages = Number(payload.totalPages) || 0;
        const lastValidPage = Math.max(nextTotalPages, 1);

        if (page > lastValidPage) {
          replacePage(lastValidPage);
          return;
        }

        setError('');
        setPosts(Array.isArray(payload.items) ? payload.items : []);
        setTotalItems(Number(payload.totalItems) || 0);
        setTotalPages(nextTotalPages);
      })
      .catch((requestError) => {
        if (!active || generation !== requestGenerationRef.current) return;
        setPosts([]);
        setTotalItems(0);
        setTotalPages(0);
        setError(getApiMessage(requestError, 'Không thể tải danh sách bài viết. Vui lòng thử lại.'));
      })
      .finally(() => {
        if (active && generation === requestGenerationRef.current) setLoadedRequestKey(requestKey);
      });

    return () => { active = false; };
  }, [page, reloadVersion, replacePage, requestKey]);

  useEffect(() => {
    let active = true;

    categoriesApi.getAll()
      .then((response) => {
        if (!active) return;
        setCategories(Array.isArray(response.data) ? response.data : []);
        setCategoryError('');
      })
      .catch((requestError) => {
        if (!active) return;
        setCategories([]);
        setCategoryError(getApiMessage(requestError, 'Không tải được tên chuyên mục.'));
      });

    return () => { active = false; };
  }, [categoryVersion]);

  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category.name])),
    [categories],
  );

  const categoryName = (categoryId) => {
    if (!categoryId) return 'Không có chuyên mục';
    return categoryById.get(categoryId) || 'Không xác định';
  };

  const changePage = (nextPage) => {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete('page');
    else next.set('page', String(nextPage));
    setSearchParams(next);
    window.scrollTo?.({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (post) => {
    if (deleteInFlightRef.current.has(post.id)) return;
    if (!window.confirm(`Xóa bài viết “${post.title}”? Hành động này sẽ ẩn bài khỏi trang tin.`)) return;

    deleteInFlightRef.current.add(post.id);
    setDeletingIds((current) => new Set(current).add(post.id));
    setDeleteError('');

    try {
      await postsApi.delete(post.id);
      if (posts.length === 1 && page > 1) changePage(page - 1);
      else setReloadVersion((version) => version + 1);
    } catch (requestError) {
      if (getApiStatus(requestError) === 401) {
        clearAuth();
        navigate('/login', { replace: true, state: { from: location } });
        return;
      }
      setDeleteError(getApiMessage(requestError, `Không thể xóa bài “${post.title}”.`));
    } finally {
      deleteInFlightRef.current.delete(post.id);
      setDeletingIds((current) => {
        const next = new Set(current);
        next.delete(post.id);
        return next;
      });
    }
  };

  return (
    <div className="bg-zinc-50/70 pb-16">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-8 sm:px-6 md:flex-row md:items-end md:justify-between lg:px-8">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-red-700">Bảng điều khiển nội dung</p>
            <h1 className="font-editorial mt-2 text-4xl font-black tracking-tight text-zinc-950 sm:text-5xl">Quản trị bài viết</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-600">Theo dõi, chỉnh sửa và xuất bản nội dung từ một danh sách phân trang an toàn.</p>
          </div>
          <Link to="/posts/new" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-red-700 px-5 text-sm font-black text-white transition-colors hover:bg-red-800">
            <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            Tạo bài viết
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-7 sm:px-6 lg:px-8">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b-2 border-zinc-950 pb-3">
          <h2 className="font-editorial text-2xl font-bold text-zinc-950">Danh sách nội dung</h2>
          <p className="text-xs font-black uppercase tracking-wider text-zinc-500">{totalItems.toLocaleString('vi-VN')} bài · Trang {page}/{Math.max(totalPages, 1)}</p>
        </div>

        {categoryError ? (
          <div role="status" aria-label="Cảnh báo chuyên mục" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            <p>{categoryError} Bài viết vẫn có thể quản lý bình thường.</p>
            <button type="button" onClick={() => setCategoryVersion((version) => version + 1)} className="min-h-11 cursor-pointer rounded-md px-3 font-black underline underline-offset-4">Tải lại chuyên mục</button>
          </div>
        ) : null}

        {deleteError ? <p role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">{deleteError}</p> : null}

        {loading ? <LoadingRows /> : null}

        {!loading && error ? (
          <section role="alert" className="rounded-xl border border-red-200 bg-white px-6 py-12 text-center">
            <h2 className="font-editorial text-2xl font-bold text-red-950">Chưa tải được bài viết</h2>
            <p className="mt-2 text-sm text-red-800">{error}</p>
            <button type="button" onClick={() => setReloadVersion((version) => version + 1)} className="mt-5 min-h-11 cursor-pointer rounded-lg bg-red-700 px-5 text-sm font-black text-white hover:bg-red-800">Thử tải lại</button>
          </section>
        ) : null}

        {!loading && !error && posts.length === 0 ? (
          <section className="rounded-xl border border-dashed border-zinc-300 bg-white px-6 py-14 text-center">
            <h2 className="font-editorial text-2xl font-bold text-zinc-950">Chưa có bài viết nào</h2>
            <p className="mt-2 text-sm text-zinc-600">Tạo bài đầu tiên để bắt đầu quản lý nội dung.</p>
          </section>
        ) : null}

        {!loading && !error && posts.length > 0 ? (
          <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
            <table className="w-full border-collapse">
              <caption className="sr-only">Danh sách bài viết dành cho quản trị viên</caption>
              <thead className="hidden bg-zinc-950 text-left text-xs uppercase tracking-wider text-white md:table-header-group">
                <tr><th scope="col" className="px-4 py-3">Bài viết</th><th scope="col" className="px-4 py-3">Chuyên mục</th><th scope="col" className="px-4 py-3">Thống kê</th><th scope="col" className="px-4 py-3 text-right">Thao tác</th></tr>
              </thead>
              <tbody className="block divide-y divide-zinc-200 md:table-row-group">
                {posts.map((post) => {
                  const deleting = deletingIds.has(post.id);
                  return (
                    <tr key={post.id} className="block p-4 md:table-row md:p-0">
                      <td className="block md:table-cell md:px-4 md:py-4">
                        <Link to={`/posts/${post.id}`} className="font-editorial text-lg font-bold text-zinc-950 transition-colors hover:text-red-700">{post.title}</Link>
                        <p className="mt-1 text-xs font-semibold text-zinc-500">Cập nhật {formatDate(post.updatedAt)}</p>
                      </td>
                      <td className="mt-3 block text-sm text-zinc-700 md:mt-0 md:table-cell md:px-4 md:py-4"><span className="mr-2 font-bold md:hidden">Chuyên mục:</span>{categoryName(post.categoryId)}</td>
                      <td className="mt-2 block text-sm font-semibold text-zinc-600 md:mt-0 md:table-cell md:px-4 md:py-4">{Number(post.views || 0).toLocaleString('vi-VN')} lượt xem</td>
                      <td className="mt-4 block md:mt-0 md:table-cell md:px-4 md:py-4">
                        <div className="flex flex-wrap gap-2 md:justify-end">
                          <Link aria-label={`Xem ${post.title}`} to={`/posts/${post.id}`} className="inline-flex min-h-11 items-center rounded-md border border-zinc-300 px-3 text-sm font-bold text-zinc-700 hover:border-zinc-950 hover:text-zinc-950">Xem</Link>
                          <Link aria-label={`Sửa ${post.title}`} to={`/posts/${post.id}/edit`} className="inline-flex min-h-11 items-center rounded-md border border-zinc-300 px-3 text-sm font-bold text-zinc-700 hover:border-red-700 hover:text-red-700">Sửa</Link>
                          <button aria-label={`Xóa ${post.title}`} type="button" disabled={deleting} onClick={() => handleDelete(post)} className="min-h-11 cursor-pointer rounded-md border border-red-200 px-3 text-sm font-bold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50">{deleting ? 'Đang xóa...' : 'Xóa'}</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        {!loading && !error && totalPages > 1 ? (
          <nav aria-label="Phân trang quản trị bài viết" className="mt-6 flex items-center justify-between gap-4">
            <button type="button" disabled={page <= 1} onClick={() => changePage(page - 1)} className="min-h-11 cursor-pointer rounded-lg border border-zinc-300 bg-white px-4 text-sm font-black text-zinc-900 hover:border-zinc-950 disabled:cursor-not-allowed disabled:opacity-40">← Trang trước</button>
            <span aria-live="polite" className="text-sm font-bold text-zinc-600">Trang {page} / {totalPages}</span>
            <button type="button" disabled={page >= totalPages} onClick={() => changePage(page + 1)} className="min-h-11 cursor-pointer rounded-lg border border-zinc-300 bg-white px-4 text-sm font-black text-zinc-900 hover:border-zinc-950 disabled:cursor-not-allowed disabled:opacity-40">Trang sau →</button>
          </nav>
        ) : null}
      </div>
    </div>
  );
}
