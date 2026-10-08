const statusClasses = {
  HIT: 'border-emerald-200 bg-emerald-100 text-emerald-950',
  MISS: 'border-amber-200 bg-amber-100 text-amber-950',
  UNKNOWN: 'border-zinc-300 bg-zinc-200 text-zinc-950',
};

export default function CacheStatusBadge({ cacheInfo }) {
  const status = cacheInfo?.status === 'HIT' || cacheInfo?.status === 'MISS'
    ? cacheInfo.status
    : 'UNKNOWN';
  const durationMs = cacheInfo?.durationMs;
  const hasDuration = Number.isFinite(durationMs) && durationMs >= 0;

  return (
    <div className="mt-5 text-sm">
      <div role="status" aria-label="Thông tin cache bài viết" aria-live="polite" className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className={`inline-flex items-center whitespace-nowrap rounded-md border px-2.5 py-1 text-xs font-black tracking-wide ${statusClasses[status]}`}>
          CACHE {status}
        </span>
        <span className="tabular-nums text-zinc-200">
          {hasDuration
            ? `Phản hồi GET: ${durationMs.toLocaleString('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ms`
            : 'Chưa đo được thời gian'}
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-zinc-300">
        Đo tại trình duyệt; không phải thời gian xử lý riêng của Redis.
      </p>
    </div>
  );
}
