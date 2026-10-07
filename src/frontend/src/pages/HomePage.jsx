import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import PostCard from '../components/PostCard';
import { postsApi } from '../services/api';
import { previewPosts } from '../data/previewPosts';

const PAGE_SIZE = 12;

function LoadingState() {
  return (
    <div role="status" aria-label="Đang tải bài viết" aria-live="polite" className="motion-safe:animate-pulse motion-reduce:animate-none">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(17rem,0.9fr)]">
        <div>
          <div className="aspect-[16/9] rounded-2xl bg-zinc-200" />
          <div className="mt-5 h-4 w-24 rounded bg-zinc-200" />
          <div className="mt-3 h-11 w-full rounded bg-zinc-200" />
          <div className="mt-3 h-6 w-4/5 rounded bg-zinc-100" />
        </div>
        <div className="space-y-6">
          {[0, 1].map((item) => (
            <div key={item} className="grid grid-cols-[9rem_1fr] gap-4 lg:grid-cols-1">
              <div className="aspect-[4/3] rounded-xl bg-zinc-200 lg:aspect-[16/8]" />
              <div className="space-y-3">
                <div className="h-4 w-20 rounded bg-zinc-200" />
                <div className="h-7 w-full rounded bg-zinc-200" />
                <div className="h-4 w-3/4 rounded bg-zinc-100" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPreview, setIsPreview] = useState(false);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [requestVersion, setRequestVersion] = useState(0);
  const categoryId = searchParams.get('categoryId') || '';
  const requestedPage = Number.parseInt(searchParams.get('page') || '1', 10);
  const page = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;

  useEffect(() => {
    let active = true;

    postsApi.getAll(page, PAGE_SIZE, categoryId)
      .then((response) => {
        if (!active) return;

        const payload = response.data;
        const items = Array.isArray(payload?.items) ? payload.items : [];
        const nextTotalPages = Number(payload?.totalPages) || 0;

        setPosts(items);
        setTotalPages(nextTotalPages);
        setTotalItems(Number(payload?.totalItems) || 0);
        setIsPreview(false);
        setError('');
      })
      .catch(() => {
        if (!active) return;

        if (import.meta.env.DEV) {
          setPosts(previewPosts);
          setTotalPages(1);
          setTotalItems(previewPosts.length);
          setIsPreview(true);
          setError('');
        } else {
          setPosts([]);
          setTotalPages(0);
          setTotalItems(0);
          setError('Không thể tải danh sách tin. Vui lòng kiểm tra kết nối API và thử lại.');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [categoryId, page, requestVersion]);

  const changePage = (nextPage) => {
    setLoading(true);
    setError('');
    const nextSearchParams = new URLSearchParams(searchParams);

    if (nextPage <= 1) {
      nextSearchParams.delete('page');
    } else {
      nextSearchParams.set('page', String(nextPage));
    }

    setSearchParams(nextSearchParams);
    document.getElementById('tin-moi')?.scrollIntoView({ block: 'start' });
  };

  const retryLoading = () => {
    setLoading(true);
    setError('');
    setRequestVersion((version) => version + 1);
  };

  const leadPost = posts[0];
  const secondaryPosts = posts.slice(1, 3);
  const latestPosts = posts.slice(3);
  const popularPosts = [...posts]
    .sort((first, second) => Number(second.views || 0) - Number(first.views || 0))
    .slice(0, 5);

  return (
    <>
      <div id="tin-moi" className="scroll-mt-32">
        <div className="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:px-6 sm:pt-9 lg:px-8">
          {isPreview ? (
            <div role="status" className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <svg viewBox="0 0 24 24" className="mt-0.5 size-5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5h.01" />
              </svg>
              <p><strong>Chế độ xem trước giao diện.</strong> Không kết nối được API nên các bài dưới đây là dữ liệu minh hoạ, chỉ xuất hiện khi chạy development.</p>
            </div>
          ) : null}

          <div className="relative mb-8 grid gap-5 overflow-hidden rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7 md:grid-cols-[minmax(0,1fr)_minmax(16rem,0.7fr)] md:items-end">
            <span aria-hidden="true" className="absolute inset-y-5 left-0 w-1 rounded-r-full bg-red-700" />
            <div className="pl-2">
              <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.18em] text-red-700">
                <span className="size-1.5 rounded-full bg-red-700" aria-hidden="true" />Dòng tin hôm nay
              </p>
              <h1 className="font-editorial mt-2 text-4xl font-bold tracking-tight text-zinc-950 sm:text-5xl lg:text-6xl">Tin tức mới nhất</h1>
            </div>
            <div className="flex flex-col gap-3 border-t border-zinc-200 pt-4 md:items-end md:border-l md:border-t-0 md:pl-6 md:pt-0 md:text-right">
              <p className="max-w-md text-sm leading-6 text-zinc-600">
                Những câu chuyện đáng chú ý, được sắp xếp để bạn nắm bắt thông tin nhanh và rõ ràng.
              </p>
              {!loading && !error ? <p className="text-xs font-bold uppercase tracking-wider text-zinc-500">{totalItems.toLocaleString('vi-VN')} bài trong dòng tin</p> : null}
            </div>
          </div>

          {loading ? <LoadingState /> : null}

          {!loading && error ? (
            <div role="alert" className="rounded-2xl border border-red-200 bg-white px-6 py-10 text-center shadow-sm">
              <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-red-50 text-red-700" aria-hidden="true">
                <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 3 22 20H2L12 3Z" /><path d="M12 9v5m0 3h.01" /></svg>
              </span>
              <h2 className="font-editorial mt-4 text-2xl font-bold text-red-950">Chưa tải được danh sách tin</h2>
              <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-red-800">{error}</p>
              <button type="button" onClick={retryLoading} className="mt-5 min-h-11 cursor-pointer rounded-lg bg-red-700 px-5 text-sm font-black text-white transition-colors hover:bg-red-800">
                Thử tải lại
              </button>
            </div>
          ) : null}

          {!loading && !error && posts.length === 0 ? (
            <div className="rounded-2xl border border-zinc-200 bg-white px-6 py-16 text-center shadow-sm">
              <h2 className="font-editorial text-2xl font-bold text-zinc-950">
                {categoryId ? 'Chuyên mục chưa có bài viết' : 'Chưa có bài viết nào'}
              </h2>
              <p className="mt-2 text-sm text-zinc-600">
                {categoryId ? 'Hãy chọn chuyên mục khác hoặc xem toàn bộ tin mới nhất.' : 'Hãy là người đầu tiên chia sẻ một câu chuyện mới.'}
              </p>
              <Link to={categoryId ? '/' : '/posts/new'} className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-zinc-950 px-5 text-sm font-black text-white hover:bg-red-700">
                {categoryId ? 'Xem tất cả tin' : 'Viết bài đầu tiên'}
              </Link>
            </div>
          ) : null}

          {!loading && !error && leadPost ? (
            <>
              <section aria-label="Tin nổi bật" className="grid gap-8 border-b border-zinc-200 pb-10 lg:grid-cols-[minmax(0,2fr)_minmax(17rem,0.9fr)]">
                <PostCard post={leadPost} variant="lead" />
                <div className="space-y-5 border-zinc-200 lg:border-l lg:pl-8">
                  {secondaryPosts.map((post) => (
                    <PostCard key={post.id} post={post} variant="secondary" />
                  ))}
                </div>
              </section>

              <section className="grid gap-10 pt-10 lg:grid-cols-[minmax(0,2fr)_minmax(17rem,0.9fr)] lg:gap-12">
                <div>
                  <div className="mb-6 flex items-center justify-between border-b border-zinc-300 pb-3">
                    <h2 className="font-editorial text-3xl font-bold text-zinc-950">Mới cập nhật</h2>
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                      {totalItems.toLocaleString('vi-VN')} bài · Trang {page}/{Math.max(totalPages, 1)}
                    </span>
                  </div>
                  <div>
                    {latestPosts.map((post) => (
                      <PostCard key={post.id} post={post} variant="horizontal" />
                    ))}
                  </div>

                  {!isPreview && totalPages > 1 ? (
                    <nav aria-label="Phân trang danh sách tin" className="mt-8 flex items-center justify-between gap-4 border-t border-zinc-200 pt-6">
                      <button type="button" disabled={page === 1} onClick={() => changePage(page - 1)} className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-zinc-300 bg-white px-4 text-sm font-black text-zinc-900 transition-colors hover:border-zinc-950 hover:bg-zinc-950 hover:text-white disabled:cursor-not-allowed disabled:opacity-40">
                        <span aria-hidden="true">←</span> Trang trước
                      </button>
                      <span className="hidden text-sm font-semibold text-zinc-600 sm:inline" aria-live="polite">
                        Trang {page} trên {totalPages}
                      </span>
                      <button type="button" disabled={page >= totalPages} onClick={() => changePage(page + 1)} className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-zinc-300 bg-white px-4 text-sm font-black text-zinc-900 transition-colors hover:border-zinc-950 hover:bg-zinc-950 hover:text-white disabled:cursor-not-allowed disabled:opacity-40">
                        Trang sau <span aria-hidden="true">→</span>
                      </button>
                    </nav>
                  ) : null}
                </div>

                <aside id="doc-nhieu" className="scroll-mt-32">
                  <div className="sticky top-32 border-t-4 border-red-700 bg-zinc-50 p-5">
                    <p className="text-xs font-black uppercase tracking-[0.16em] text-red-700">Redis INCR</p>
                    <h2 className="font-editorial mt-1 text-3xl font-bold text-zinc-950">Đọc nhiều</h2>
                    <ol className="mt-5">
                      {popularPosts.map((post, index) => (
                        <li key={post.id} className="border-b border-zinc-200 py-4 first:pt-0 last:border-0 last:pb-0">
                          <Link to={`/posts/${post.id}`} className="group grid grid-cols-[2.25rem_1fr] gap-3">
                            <span className="font-editorial text-2xl font-bold text-red-700">{String(index + 1).padStart(2, '0')}</span>
                            <span>
                              <span className="font-editorial line-clamp-2 text-lg font-bold leading-snug text-zinc-950 transition-colors group-hover:text-red-700">{post.title}</span>
                              <span className="mt-1 block text-xs font-semibold text-zinc-500">{Number(post.views || 0).toLocaleString('vi-VN')} lượt xem</span>
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ol>
                  </div>
                </aside>
              </section>
            </>
          ) : null}
        </div>
      </div>

    </>
  );
}
