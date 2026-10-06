import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { postsApi } from '../services/api';

const pendingPostRequests = new Map();

function getPostByIdOnce(id) {
  const pendingRequest = pendingPostRequests.get(id);
  if (pendingRequest) return pendingRequest;

  const request = postsApi.getById(id);
  pendingPostRequests.set(id, request);
  request.then(
    () => pendingPostRequests.delete(id),
    () => pendingPostRequests.delete(id),
  );

  return request;
}

function formatPostDate(value) {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? 'Chưa cập nhật'
    : date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      });
}

function LoadingState() {
  return (
    <div aria-label="Đang tải bài viết" aria-live="polite" className="mx-auto max-w-5xl animate-pulse px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="h-3 w-24 rounded bg-red-100" />
        <div className="mt-5 h-12 w-full rounded bg-zinc-200" />
        <div className="mt-3 h-12 w-4/5 rounded bg-zinc-200" />
        <div className="mt-6 h-4 w-64 rounded bg-zinc-100" />
      </div>
      <div className="mt-9 aspect-[16/9] rounded-2xl bg-zinc-200" />
      <div className="mx-auto mt-9 max-w-3xl space-y-3">
        {[100, 92, 96, 76].map((width) => (
          <div key={width} className="h-5 rounded bg-zinc-100" style={{ width: `${width}%` }} />
        ))}
      </div>
    </div>
  );
}

export default function PostDetailPage() {
  const { id } = useParams();
  const countedPostIdRef = useRef(null);
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [viewError, setViewError] = useState(false);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadPost() {
      setLoading(true);
      setError('');
      setViewError(false);

      try {
        const response = await getPostByIdOnce(id);
        if (!active) return;

        setPost(response.data);
        setLoading(false);

        if (countedPostIdRef.current !== id) {
          countedPostIdRef.current = id;

          try {
            const viewResponse = await postsApi.incrementView(id);
            if (active) {
              setPost((currentPost) => (
                currentPost?.id === id
                  ? { ...currentPost, views: viewResponse.data.views }
                  : currentPost
              ));
            }
          } catch {
            if (active) setViewError(true);
          }
        }
      } catch (requestError) {
        if (!active) return;

        setPost(null);
        setError(requestError.response?.data?.message || 'Không thể tải bài viết. Vui lòng thử lại.');
      } finally {
        if (active) setLoading(false);
      }
    }

    loadPost();

    return () => {
      active = false;
    };
  }, [id, requestVersion]);

  if (loading) return <LoadingState />;

  if (error || !post) {
    return (
      <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6 sm:py-24" aria-labelledby="post-error-title">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-red-700">Không tải được bài viết</p>
        <h1 id="post-error-title" className="font-editorial mt-3 text-3xl font-bold text-zinc-950 sm:text-4xl">
          Nội dung này hiện không khả dụng
        </h1>
        <p role="alert" className="mx-auto mt-4 max-w-xl text-base leading-7 text-zinc-600">
          {error || 'Bài viết không tồn tại hoặc đã bị xóa.'}
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={() => setRequestVersion((version) => version + 1)}
            className="inline-flex min-h-11 cursor-pointer items-center rounded-lg bg-red-700 px-5 text-sm font-black text-white transition-colors hover:bg-red-800"
          >
            Thử tải lại
          </button>
          <Link
            to="/"
            className="inline-flex min-h-11 items-center rounded-lg border border-zinc-300 bg-white px-5 text-sm font-black text-zinc-900 transition-colors hover:border-zinc-950 hover:bg-zinc-950 hover:text-white"
          >
            Về trang chủ
          </Link>
        </div>
      </section>
    );
  }

  return (
    <article className="pb-16 sm:pb-24">
      <header className="border-b border-zinc-200 bg-zinc-50">
        <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
          <Link to="/" className="inline-flex min-h-11 items-center text-sm font-bold text-zinc-600 transition-colors hover:text-red-700">
            Trở về trang tin
          </Link>
          <p className="mt-5 text-xs font-black uppercase tracking-[0.16em] text-red-700">Bài viết</p>
          <h1 className="font-editorial mt-3 break-words text-4xl font-black leading-[1.12] text-zinc-950 sm:text-5xl lg:text-6xl">
            {post.title}
          </h1>
          <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm font-semibold text-zinc-500">
            <time dateTime={post.createdAt}>Đăng ngày {formatPostDate(post.createdAt)}</time>
            <span aria-hidden="true" className="size-1 rounded-full bg-red-600" />
            <span aria-live="polite">{Number(post.views || 0).toLocaleString('vi-VN')} lượt xem</span>
          </div>
          {viewError ? (
            <p role="status" className="mt-3 text-sm text-amber-800">
              Lượt xem chưa được cập nhật, nhưng bạn vẫn có thể đọc bài viết.
            </p>
          ) : null}
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        {post.imageUrl ? (
          <div className="mt-8 overflow-hidden rounded-2xl bg-zinc-100 sm:mt-10">
            <img
              src={post.imageUrl}
              alt={`Ảnh minh họa cho bài viết ${post.title}`}
              className="aspect-[16/9] w-full object-cover"
              onError={(event) => { event.currentTarget.parentElement.style.display = 'none'; }}
            />
          </div>
        ) : null}

        <div className="mx-auto mt-9 max-w-3xl sm:mt-12">
          <div className="break-words whitespace-pre-line text-[1.0625rem] leading-8 text-zinc-700 sm:text-lg sm:leading-9">
            {post.content}
          </div>
          <div className="mt-12 border-t border-zinc-200 pt-6">
            <Link to="/" className="inline-flex min-h-11 items-center text-sm font-black text-red-700 transition-colors hover:text-red-900">
              Xem thêm bài viết khác
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
