import { Link } from 'react-router-dom';

function formatPostDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Chưa cập nhật'
    : date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function makeExcerpt(content = '', maxLength = 150) {
  const normalized = content.replace(/\s+/g, ' ').trim();
  return normalized.length > maxLength
    ? `${normalized.slice(0, maxLength - 3)}...`
    : normalized;
}

function PostImage({ post, eager = false, className = '' }) {
  return (
    <div className={`relative overflow-hidden bg-gradient-to-br from-zinc-900 via-red-950 to-red-700 ${className}`}>
      <div className="absolute inset-0 grid place-items-center text-white">
        <svg viewBox="0 0 24 24" className="size-10 opacity-30" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
          <path d="M4 5.5h12.5A2.5 2.5 0 0 1 19 8v10.5H6.5A2.5 2.5 0 0 1 4 16V5.5Z" />
          <path d="M7.5 9h8M7.5 12h8M7.5 15h4" />
        </svg>
      </div>
      {post.imageUrl ? (
        <img
          src={post.imageUrl}
          alt=""
          loading={eager ? 'eager' : 'lazy'}
          onError={(event) => { event.currentTarget.style.display = 'none'; }}
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.025]"
        />
      ) : null}
    </div>
  );
}

function Meta({ post }) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-semibold text-zinc-500">
      <time dateTime={post.createdAt}>{formatPostDate(post.createdAt)}</time>
      <span aria-hidden="true" className="size-1 rounded-full bg-red-500" />
      <span className="inline-flex items-center gap-1.5">
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
          <circle cx="12" cy="12" r="2.5" />
        </svg>
        {Number(post.views || 0).toLocaleString('vi-VN')} lượt xem
      </span>
    </div>
  );
}

export default function PostCard({ post, variant = 'grid' }) {
  if (variant === 'lead') {
    return (
      <Link to={`/posts/${post.id}`} className="group block min-w-0">
        <PostImage post={post} eager className="aspect-[16/9] rounded-2xl" />
        <div className="pt-5">
          <span className="text-xs font-black uppercase tracking-[0.16em] text-red-700">Tin nổi bật</span>
          <h2 className="font-editorial mt-2 text-3xl font-bold leading-tight text-zinc-950 transition-colors group-hover:text-red-700 sm:text-4xl lg:text-[2.75rem]">
            {post.title}
          </h2>
          <p className="mt-3 max-w-3xl text-base leading-7 text-zinc-600">{makeExcerpt(post.content, 210)}</p>
          <div className="mt-4"><Meta post={post} /></div>
        </div>
      </Link>
    );
  }

  if (variant === 'secondary') {
    return (
      <Link to={`/posts/${post.id}`} className="group grid grid-cols-[7.5rem_minmax(0,1fr)] gap-4 border-b border-zinc-200 pb-5 last:border-0 last:pb-0 sm:grid-cols-[9rem_minmax(0,1fr)] lg:grid-cols-1">
        <PostImage post={post} className="aspect-[4/3] rounded-xl lg:aspect-[16/8]" />
        <div className="min-w-0">
          <span className="text-[11px] font-black uppercase tracking-[0.14em] text-red-700">Đáng chú ý</span>
          <h3 className="font-editorial mt-1.5 line-clamp-3 text-xl font-bold leading-snug text-zinc-950 transition-colors group-hover:text-red-700">
            {post.title}
          </h3>
          <div className="mt-3"><Meta post={post} /></div>
        </div>
      </Link>
    );
  }

  if (variant === 'horizontal') {
    return (
      <Link to={`/posts/${post.id}`} className="group grid grid-cols-[7.5rem_minmax(0,1fr)] gap-4 border-b border-zinc-200 py-5 first:pt-0 sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-6">
        <PostImage post={post} className="aspect-[4/3] rounded-xl" />
        <div className="min-w-0 self-center">
          <h3 className="font-editorial line-clamp-2 text-xl font-bold leading-snug text-zinc-950 transition-colors group-hover:text-red-700 sm:text-2xl">
            {post.title}
          </h3>
          <p className="mt-2 hidden line-clamp-2 text-sm leading-6 text-zinc-600 sm:block">{makeExcerpt(post.content, 130)}</p>
          <div className="mt-3"><Meta post={post} /></div>
        </div>
      </Link>
    );
  }

  return (
    <Link to={`/posts/${post.id}`} className="group flex h-full flex-col">
      <PostImage post={post} className="aspect-[16/10] rounded-xl" />
      <div className="flex flex-1 flex-col pt-4">
        <h3 className="font-editorial line-clamp-2 text-xl font-bold leading-snug text-zinc-950 transition-colors group-hover:text-red-700">
          {post.title}
        </h3>
        <p className="mt-2 line-clamp-2 text-sm leading-6 text-zinc-600">{makeExcerpt(post.content, 110)}</p>
        <div className="mt-auto pt-4"><Meta post={post} /></div>
      </div>
    </Link>
  );
}
