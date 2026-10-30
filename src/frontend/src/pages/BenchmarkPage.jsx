import { useEffect, useRef, useState } from 'react';
import { benchmarkApi, postsApi } from '../services/api';
import { getApiMessage, getApiStatus } from '../utils/apiError';
import { parsePostLink, runBatch, summarizeRounds } from '../utils/benchmark';

const DEFAULT_COUNT = 100;
const DEFAULT_ROUNDS = 3;
const MAX_COUNT = 1000;
const MAX_ROUNDS = 10;

const MODES = {
  redis: {
    label: 'Có Redis',
    detail: 'GET /api/posts/{id} · Cache-Aside',
    bar: 'bg-red-700',
    text: 'text-red-700',
    stroke: '#b91c1c',
  },
  mongo: {
    label: 'Không Redis',
    detail: 'GET /api/posts/slug/{slug} · đọc thẳng MongoDB',
    bar: 'bg-emerald-700',
    text: 'text-emerald-700',
    stroke: '#047857',
  },
};

function formatMs(value, digits = 1) {
  if (!Number.isFinite(value)) return '—';
  return `${value.toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits })} ms`;
}

function formatRatio(value) {
  return Number.isFinite(value)
    ? `${value.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} lần`
    : '—';
}

function clampInt(value, min, max, fallback) {
  const number = Math.floor(Number(value));
  return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback;
}

function Sparkline({ latencies, count, stroke }) {
  if (!latencies?.length) {
    return <div className="h-12 rounded-md bg-zinc-100" aria-hidden="true" />;
  }
  const max = Math.max(...latencies, 1);
  const width = 200;
  const height = 48;
  const step = width / Math.max(count - 1, 1);
  const points = latencies
    .map((value, index) => `${(index * step).toFixed(1)},${(height - 2 - (value / max) * (height - 6)).toFixed(1)}`)
    .join(' ');

  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="h-12 w-full rounded-md bg-zinc-50" aria-hidden="true">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function ModeCard({ mode, run, live, count, active }) {
  const meta = MODES[mode];
  const source = live ?? run;
  const done = live ? live.done : run?.count ?? 0;
  const elapsed = live ? live.elapsedMs : run?.totalMs;
  const average = done > 0 && Number.isFinite(elapsed) ? elapsed / done : null;
  const last = source?.latencies?.at(-1);
  const percent = count > 0 ? Math.round((done / count) * 100) : 0;

  return (
    <article className={`rounded-2xl border bg-white p-5 shadow-sm transition-colors sm:p-6 ${active ? 'border-zinc-900' : 'border-zinc-200'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className={`text-lg font-black ${meta.text}`}>{meta.label}</h3>
          <p className="mt-0.5 truncate font-mono text-xs text-zinc-500">{meta.detail}</p>
        </div>
        <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${active ? 'bg-zinc-900 text-white' : run?.complete ? 'bg-zinc-100 text-zinc-700' : 'bg-zinc-100 text-zinc-400'}`}>
          {active ? <span className="size-1.5 animate-pulse rounded-full bg-emerald-400 motion-reduce:animate-none" aria-hidden="true" /> : null}
          {active ? 'Đang chạy' : run?.complete ? 'Xong' : run ? 'Đã dừng' : 'Chờ'}
        </span>
      </div>

      <p className="mt-5 text-xs font-bold uppercase tracking-[0.14em] text-zinc-500">Tổng thời gian</p>
      <p className="mt-1 font-editorial text-4xl font-bold tabular-nums text-zinc-950">{formatMs(elapsed)}</p>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-zinc-100" role="progressbar" aria-label={`Tiến độ ${meta.label}`} aria-valuemin={0} aria-valuemax={count} aria-valuenow={done}>
        <div className={`h-full ${meta.bar}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-1.5 text-xs tabular-nums text-zinc-500">{done.toLocaleString('vi-VN')} / {count.toLocaleString('vi-VN')} request</p>

      <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
        <div>
          <dt className="text-xs text-zinc-500">TB / request</dt>
          <dd className="font-bold tabular-nums">{formatMs(average, 2)}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500">Request cuối</dt>
          <dd className="font-bold tabular-nums">{formatMs(last, 2)}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500">{mode === 'redis' ? 'HIT / MISS' : 'Lỗi'}</dt>
          <dd className="font-bold tabular-nums">
            {mode === 'redis'
              ? `${(source?.hit ?? 0).toLocaleString('vi-VN')} / ${(source?.miss ?? 0).toLocaleString('vi-VN')}`
              : (source?.errors ?? 0).toLocaleString('vi-VN')}
          </dd>
        </div>
      </dl>

      <div className="mt-4">
        <p className="mb-1.5 text-xs text-zinc-500">Độ trễ từng request</p>
        <Sparkline latencies={source?.latencies} count={count} stroke={meta.stroke} />
      </div>
    </article>
  );
}

export default function BenchmarkPage() {
  const [link, setLink] = useState('');
  const [countInput, setCountInput] = useState(String(DEFAULT_COUNT));
  const [roundsInput, setRoundsInput] = useState(String(DEFAULT_ROUNDS));
  const [running, setRunning] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [error, setError] = useState('');
  const [post, setPost] = useState(null);
  const [plan, setPlan] = useState({ count: DEFAULT_COUNT, rounds: DEFAULT_ROUNDS });
  const [results, setResults] = useState([]);
  const [live, setLive] = useState(null);
  const stopRef = useRef(false);

  useEffect(() => () => { stopRef.current = true; }, []);

  const summary = summarizeRounds(results);
  const currentRound = live?.round ?? results.length;
  const shownRound = results.find((round) => round.round === currentRound);
  const barMax = Math.max(summary.redisAvgMs ?? 0, summary.mongoAvgMs ?? 0, 1);

  const saveRun = (roundNo, mode, run) => {
    setResults((current) => {
      const next = current.some((round) => round.round === roundNo)
        ? current.map((round) => (round.round === roundNo ? { ...round, [mode]: run } : round))
        : [...current, { round: roundNo, [mode]: run }];
      return next;
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (running) return;

    const target = parsePostLink(link);
    if (!target) {
      setError('Dán link bài viết dạng …/posts/{id}, ID 24 ký tự hoặc slug của bài.');
      return;
    }
    const count = clampInt(countInput, 1, MAX_COUNT, DEFAULT_COUNT);
    const rounds = clampInt(roundsInput, 1, MAX_ROUNDS, DEFAULT_ROUNDS);
    setCountInput(String(count));
    setRoundsInput(String(rounds));

    stopRef.current = false;
    setRunning(true);
    setStopped(false);
    setError('');
    setResults([]);
    setLive(null);
    setPlan({ count, rounds });

    try {
      const response = target.id ? await postsApi.getById(target.id) : await benchmarkApi.findBySlug(target.slug);
      const found = { id: response.data.id, slug: response.data.slug, title: response.data.title };
      setPost(found);

      // Khởi động: nạp sẵn post:{id} vào Redis và làm nóng kết nối MongoDB, không tính giờ.
      await benchmarkApi.withRedis(found.id);
      await benchmarkApi.withoutRedis(found.slug);

      const requests = {
        redis: () => benchmarkApi.withRedis(found.id),
        mongo: () => benchmarkApi.withoutRedis(found.slug),
      };

      for (let roundNo = 1; roundNo <= rounds && !stopRef.current; roundNo += 1) {
        // Lần chẵn đổi thứ tự để không chế độ nào luôn được chạy sau.
        const order = roundNo % 2 === 1 ? ['redis', 'mongo'] : ['mongo', 'redis'];
        for (const mode of order) {
          if (stopRef.current) break;
          const run = await runBatch({
            request: requests[mode],
            count,
            shouldStop: () => stopRef.current,
            onProgress: (progress) => setLive({ round: roundNo, mode, ...progress, latencies: [...progress.latencies] }),
          });
          saveRun(roundNo, mode, { ...run, complete: run.count === count });
        }
      }
    } catch (requestError) {
      setError(getApiStatus(requestError) === 404
        ? 'Không tìm thấy bài viết này hoặc bài đã bị xóa.'
        : getApiMessage(requestError, 'Không gọi được API. Kiểm tra backend đã chạy chưa.'));
    } finally {
      setStopped(stopRef.current);
      setLive(null);
      setRunning(false);
    }
  };

  const inputClass = 'min-h-12 w-full rounded-lg border border-white/15 bg-white/[0.08] px-4 text-base text-white placeholder:text-zinc-500 focus:border-red-400 focus:outline-none focus:ring-2 focus:ring-red-500/30 disabled:opacity-60';

  return (
    <div className="min-h-[60vh] bg-zinc-100/70 pb-16">
      <header className="relative isolate overflow-hidden border-b border-zinc-800 bg-zinc-950 text-white">
        <div aria-hidden="true" className="absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(ellipse_at_top_right,rgba(185,28,28,0.24),transparent_65%)] md:block" />
        <div className="relative mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.06] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-zinc-300">
            <span className={`size-1.5 rounded-full ${running ? 'animate-pulse bg-emerald-400 motion-reduce:animate-none' : 'bg-red-500'}`} aria-hidden="true" />
            Đo hiệu năng trực tiếp
          </div>
          <h1 className="mt-5 max-w-3xl font-editorial text-5xl font-bold leading-tight text-white sm:text-6xl">Có Redis và không Redis<span className="text-red-500">.</span></h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-300">
            Dán link một bài viết. Mỗi lần đo gửi lần lượt từng request tới cùng bài ở hai chế độ và ghi tổng thời gian; sau các lần đo, trang tính thời gian trung bình.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,1fr)_8rem_8rem_auto] lg:items-end">
            <label className="block min-w-0" htmlFor="benchmark-link">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-zinc-400">Link bài viết</span>
              <input
                id="benchmark-link"
                type="text"
                inputMode="url"
                value={link}
                onChange={(event) => setLink(event.target.value)}
                placeholder="http://localhost:3000/posts/6ac6bf1b5cdee79754d461f0"
                disabled={running}
                className={inputClass}
                autoComplete="off"
              />
            </label>
            <label className="block" htmlFor="benchmark-count">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-zinc-400">Request</span>
              <input id="benchmark-count" type="number" min={1} max={MAX_COUNT} value={countInput} onChange={(event) => setCountInput(event.target.value)} disabled={running} className={`${inputClass} tabular-nums`} />
            </label>
            <label className="block" htmlFor="benchmark-rounds">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-zinc-400">Số lần đo</span>
              <input id="benchmark-rounds" type="number" min={1} max={MAX_ROUNDS} value={roundsInput} onChange={(event) => setRoundsInput(event.target.value)} disabled={running} className={`${inputClass} tabular-nums`} />
            </label>
            {running ? (
              <button type="button" onClick={() => { stopRef.current = true; }} className="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-lg border border-white/25 px-6 text-sm font-black text-white transition-colors hover:bg-white/10">
                <span className="size-2.5 rounded-sm bg-white" aria-hidden="true" />
                Dừng
              </button>
            ) : (
              <button type="submit" className="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-lg bg-red-700 px-6 text-sm font-black text-white shadow-lg shadow-red-950/20 transition-colors hover:bg-red-600">
                <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden="true"><path d="M7 5v14l11-7z" /></svg>
                Bắt đầu đo
              </button>
            )}
          </form>
          {error ? <p role="alert" className="mt-4 max-w-2xl rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p> : null}
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-8 px-4 pt-8 sm:px-6 lg:px-8">
        {post ? (
          <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
            <p className="min-w-0 text-sm text-zinc-600">
              Bài đang đo: <span className="font-bold text-zinc-950">{post.title}</span>
            </p>
            <p className="font-mono text-xs text-zinc-500">{post.id}</p>
          </div>
        ) : null}

        <section aria-labelledby="benchmark-live" className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="benchmark-live" className="text-xl font-black text-zinc-950">
              {currentRound > 0 ? `Lần đo ${currentRound} / ${plan.rounds}` : 'Kết quả trực tiếp'}
            </h2>
            <p className="text-sm text-zinc-500" aria-live="polite">
              {running ? (live ? `Đang chạy: ${MODES[live.mode].label}` : 'Đang chuẩn bị…') : stopped ? 'Đã dừng giữa chừng' : results.length ? 'Đã xong' : 'Chưa chạy'}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {['redis', 'mongo'].map((mode) => (
              <ModeCard
                key={mode}
                mode={mode}
                count={plan.count}
                run={shownRound?.[mode]}
                live={live?.mode === mode ? live : null}
                active={live?.mode === mode}
              />
            ))}
          </div>
        </section>

        <section aria-labelledby="benchmark-results" className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="min-w-0 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 id="benchmark-results" className="text-lg font-black text-zinc-950">Tổng thời gian từng lần đo</h2>
            <p className="mt-1 text-sm text-zinc-500">{plan.count.toLocaleString('vi-VN')} request mỗi chế độ, gửi tuần tự.</p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm tabular-nums">
                <thead>
                  <tr className="border-b border-zinc-200 text-left text-xs uppercase tracking-wide text-zinc-500">
                    <th className="py-2 pr-4 font-bold">Lần</th>
                    <th className="py-2 pr-4 text-right font-bold text-red-700">Có Redis</th>
                    <th className="py-2 pr-4 text-right font-bold text-emerald-700">Không Redis</th>
                    <th className="py-2 pr-4 text-right font-bold">Chênh lệch</th>
                    <th className="py-2 text-right font-bold">Redis nhanh hơn</th>
                  </tr>
                </thead>
                <tbody>
                  {results.length === 0 ? (
                    <tr><td colSpan={5} className="py-6 text-center text-zinc-400">Chưa có lần đo nào.</td></tr>
                  ) : results.map((round) => {
                    const both = round.redis?.complete && round.mongo?.complete;
                    return (
                      <tr key={round.round} className="border-b border-zinc-100">
                        <td className="py-2.5 pr-4 font-bold">Lần {round.round}</td>
                        <td className="py-2.5 pr-4 text-right">{round.redis ? formatMs(round.redis.totalMs) : '—'}</td>
                        <td className="py-2.5 pr-4 text-right">{round.mongo ? formatMs(round.mongo.totalMs) : '—'}</td>
                        <td className="py-2.5 pr-4 text-right">{both ? formatMs(round.mongo.totalMs - round.redis.totalMs) : '—'}</td>
                        <td className="py-2.5 text-right font-bold">{both ? formatRatio(round.mongo.totalMs / round.redis.totalMs) : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
                {summary.redisAvgMs !== null || summary.mongoAvgMs !== null ? (
                  <tfoot>
                    <tr className="font-black text-zinc-950">
                      <td className="pt-3 pr-4">Trung bình</td>
                      <td className="pt-3 pr-4 text-right text-red-700">{formatMs(summary.redisAvgMs)}</td>
                      <td className="pt-3 pr-4 text-right text-emerald-700">{formatMs(summary.mongoAvgMs)}</td>
                      <td className="pt-3 pr-4 text-right">{summary.speedup ? formatMs(summary.mongoAvgMs - summary.redisAvgMs) : '—'}</td>
                      <td className="pt-3 text-right">{formatRatio(summary.speedup)}</td>
                    </tr>
                  </tfoot>
                ) : null}
              </table>
            </div>
            <p className="mt-4 text-xs leading-5 text-zinc-500">
              Chỉ tính lần đo chạy đủ số request. Thời gian đo tại trình duyệt, gồm cả mạng nội bộ và xử lý của API. Lần chẵn chạy chế độ không Redis trước để thứ tự không thiên vị một bên.
            </p>
          </div>

          <aside aria-label="Trung bình" className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5 text-white shadow-sm sm:p-6">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-zinc-400">Trung bình tổng thời gian</p>
            <p className="mt-3 font-editorial text-5xl font-bold tabular-nums">{formatRatio(summary.speedup)}</p>
            <p className="mt-1 text-sm text-zinc-400">Redis nhanh hơn đọc thẳng MongoDB</p>
            <div className="mt-6 space-y-4">
              {[['redis', summary.redisAvgMs], ['mongo', summary.mongoAvgMs]].map(([mode, value]) => (
                <div key={mode}>
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span className="font-bold">{MODES[mode].label}</span>
                    <span className="tabular-nums text-zinc-300">{formatMs(value)}</span>
                  </div>
                  <div className="mt-1.5 h-3 overflow-hidden rounded-full bg-white/10">
                    <div className={`h-full rounded-full ${mode === 'redis' ? 'bg-red-500' : 'bg-emerald-500'} transition-[width] duration-300`} style={{ width: `${((value ?? 0) / barMax) * 100}%` }} />
                  </div>
                  <p className="mt-1 text-xs tabular-nums text-zinc-500">
                    {Number.isFinite(value) ? `${formatMs(value / plan.count, 2)} mỗi request` : 'Chưa có số liệu'}
                  </p>
                </div>
              ))}
            </div>
          </aside>
        </section>
      </div>
    </div>
  );
}
