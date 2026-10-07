import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { authApi } from '../services/api';
import { getApiMessage, getApiStatus } from '../utils/apiError';

const POLL_INTERVAL_MS = 30_000;

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' });
}

function formatDuration(seconds) {
  const remaining = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = Math.floor(remaining / 60);
  const remainder = remaining % 60;
  return minutes > 0 ? `${minutes} phút ${remainder} giây` : `${remainder} giây`;
}

function getInitials(username) {
  return String(username || '?')
    .trim()
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase('vi-VN'))
    .join('');
}

function LoadingSessions() {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">Đang tải danh sách phiên đăng nhập...</span>
      {[0, 1].map((item) => (
        <div key={item} className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-6">
          <div className="flex animate-pulse items-start gap-4 motion-reduce:animate-none">
            <div className="size-12 shrink-0 rounded-2xl bg-zinc-200" />
            <div className="min-w-0 flex-1 space-y-3 pt-1">
              <div className="h-4 w-36 rounded bg-zinc-200" />
              <div className="h-3 w-24 rounded bg-zinc-100" />
              <div className="grid gap-3 pt-3 sm:grid-cols-3">
                <div className="h-12 rounded-lg bg-zinc-100" />
                <div className="h-12 rounded-lg bg-zinc-100" />
                <div className="h-12 rounded-lg bg-zinc-100" />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AdminSessionsPage() {
  const { clearAuth } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [secondsElapsed, setSecondsElapsed] = useState(0);
  const [revokingIds, setRevokingIds] = useState(() => new Set());
  const requestGenerationRef = useRef(0);
  const revokeInFlightRef = useRef(new Set());

  const redirectToLogin = useCallback(() => {
    clearAuth();
    navigate('/login', { replace: true, state: { from: location } });
  }, [clearAuth, location, navigate]);

  const currentSessionCount = sessions.filter((session) => session.isCurrent).length;
  const revocableSessionCount = sessions.filter((session) => !session.isCurrent).length;
  const summaryUnavailable = sessions.length === 0 && (loading || Boolean(error));
  const sessionCountLabel = summaryUnavailable ? '—' : sessions.length.toLocaleString('vi-VN');
  const currentCountLabel = summaryUnavailable ? '—' : currentSessionCount;
  const revocableCountLabel = summaryUnavailable ? '—' : revocableSessionCount;
  const refreshInSeconds = Math.max(0, 30 - (secondsElapsed % 30));
  const connectionLabel = error ? 'Kết nối gián đoạn' : loading ? 'Đang đồng bộ' : 'Trực tiếp';
  const connectionDot = error ? 'bg-red-400' : loading ? 'bg-amber-300' : 'bg-emerald-400';

  const loadSessions = useCallback(async () => {
    const generation = ++requestGenerationRef.current;
    setLoading(true);
    try {
      const response = await authApi.getActiveSessions();
      if (generation !== requestGenerationRef.current) return;
      setSessions(Array.isArray(response.data) ? response.data : []);
      setError('');
      setSecondsElapsed(0);
    } catch (requestError) {
      if (generation !== requestGenerationRef.current) return;
      if (getApiStatus(requestError) === 401) {
        redirectToLogin();
        return;
      }
      if (getApiStatus(requestError) === 403) setSessions([]);
      setError(getApiMessage(requestError, 'Không thể tải danh sách phiên. Vui lòng thử lại.'));
    } finally {
      if (generation === requestGenerationRef.current) setLoading(false);
    }
  }, [redirectToLogin]);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (active) loadSessions();
    });
    const poll = window.setInterval(() => {
      if (document.visibilityState === 'visible') loadSessions();
    }, POLL_INTERVAL_MS);
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') loadSessions();
    };
    window.addEventListener('focus', refreshWhenVisible);
    document.addEventListener('visibilitychange', refreshWhenVisible);
    return () => {
      active = false;
      requestGenerationRef.current += 1;
      window.clearInterval(poll);
      window.removeEventListener('focus', refreshWhenVisible);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
    };
  }, [loadSessions]);

  useEffect(() => {
    if (loading || error || sessions.length === 0) return undefined;
    const tick = window.setInterval(() => setSecondsElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(tick);
  }, [error, loading, sessions.length]);

  const handleRevoke = async (session) => {
    if (session.isCurrent || revokeInFlightRef.current.has(session.sessionId)) return;
    if (!window.confirm(`Thu hồi phiên đăng nhập của ${session.username}? Người dùng sẽ cần đăng nhập lại.`)) return;

    revokeInFlightRef.current.add(session.sessionId);
    setRevokingIds((current) => new Set(current).add(session.sessionId));
    setError('');
    try {
      await authApi.revokeSession(session.sessionId);
      await loadSessions();
    } catch (requestError) {
      const status = getApiStatus(requestError);
      if (status === 401) {
        redirectToLogin();
        return;
      }
      if (status === 404) {
        await loadSessions();
        return;
      }
      if (status === 403) setSessions([]);
      setError(getApiMessage(requestError, `Không thể thu hồi phiên của ${session.username}.`));
    } finally {
      revokeInFlightRef.current.delete(session.sessionId);
      setRevokingIds((current) => {
        const next = new Set(current);
        next.delete(session.sessionId);
        return next;
      });
    }
  };

  return (
    <div className="min-h-[60vh] bg-zinc-100/70 pb-16">
      <header className="relative isolate overflow-hidden border-b border-zinc-800 bg-zinc-950 text-white">
        <div aria-hidden="true" className="absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(ellipse_at_top_right,rgba(185,28,28,0.24),transparent_65%)] md:block" />
        <div className="relative mx-auto grid max-w-7xl gap-9 px-4 py-10 sm:px-6 sm:py-14 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-center lg:px-8 lg:py-16">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.06] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-zinc-300">
              <span className="size-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
              Trung tâm bảo mật
            </div>
            <h1 className="mt-5 max-w-3xl font-serif text-5xl font-bold leading-[0.98] tracking-[-0.045em] text-white sm:text-6xl lg:text-7xl">Phiên truy cập<span className="text-red-500">.</span></h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-zinc-300 sm:text-lg">Theo dõi các phiên đăng nhập đang mở. Thu hồi phiên lạ để buộc tài khoản đăng nhập lại.</p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <button type="button" onClick={loadSessions} disabled={loading} className="group inline-flex min-h-12 cursor-pointer items-center gap-2.5 rounded-lg bg-red-700 px-5 text-sm font-black text-white shadow-lg shadow-red-950/20 transition-colors duration-200 hover:bg-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:cursor-wait disabled:opacity-60">
                <svg viewBox="0 0 24 24" className={`size-4 ${loading ? 'animate-spin motion-reduce:animate-none' : 'transition-transform duration-200 group-hover:-rotate-45'}`} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M20 7v5h-5M4 17v-5h5" />
                  <path d="M5.6 9a7 7 0 0 1 11.9-2L20 12M4 12l2.5 5a7 7 0 0 0 11.9-2" />
                </svg>
                Làm mới danh sách
              </button>
              <p className="text-sm text-zinc-400" aria-live="polite">
                {secondsElapsed === 0 ? 'Dữ liệu vừa cập nhật' : `Cập nhật ${secondsElapsed} giây trước`}
              </p>
            </div>
          </div>

          <aside aria-label="Tóm tắt phiên đăng nhập" className="rounded-2xl border border-white/10 bg-white/[0.06] p-5 shadow-2xl shadow-black/10 sm:p-6">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-zinc-400">Đang theo dõi</p>
              <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-bold ${error ? 'bg-red-400/10 text-red-300' : loading ? 'bg-amber-300/10 text-amber-200' : 'bg-emerald-400/10 text-emerald-300'}`}>
                <span className={`size-1.5 rounded-full ${connectionDot}`} aria-hidden="true" />{connectionLabel}
              </span>
            </div>
            <div className="mt-4 flex items-baseline gap-3 border-b border-white/10 pb-5">
              <span className="font-serif text-6xl font-bold leading-none tracking-tight tabular-nums text-white">{sessionCountLabel}</span>
              <span className="text-sm font-medium text-zinc-400">phiên hoạt động</span>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <dt className="text-xs font-semibold text-zinc-400">Phiên của bạn</dt>
                <dd className="mt-1 text-2xl font-bold tabular-nums text-white">{currentCountLabel}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-zinc-400">Có thể thu hồi</dt>
                <dd className="mt-1 text-2xl font-bold tabular-nums text-white">{revocableCountLabel}</dd>
              </div>
            </dl>
          </aside>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <section aria-labelledby="sessions-heading">
          <div className="mb-5 flex flex-col gap-4 border-b border-zinc-300 pb-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.17em] text-red-700">Sổ phiên đăng nhập</p>
              <h2 id="sessions-heading" className="mt-1 font-serif text-3xl font-bold tracking-tight text-zinc-950 sm:text-4xl">Tài khoản đang hoạt động</h2>
            </div>
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-zinc-300 bg-white px-3.5 py-2 text-xs font-bold text-zinc-600 shadow-sm">
              <svg viewBox="0 0 24 24" className="size-4 text-red-700" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </svg>
              Tự làm mới sau {refreshInSeconds} giây
            </div>
          </div>

          {error ? (
            <section role="alert" className="flex flex-col gap-5 rounded-2xl border border-red-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-6">
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-red-50 text-red-700">
                  <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M12 3 22 20H2L12 3Z" /><path d="M12 9v5m0 3h.01" /></svg>
                </span>
                <div>
                  <h3 className="font-bold text-zinc-950">Chưa thể cập nhật danh sách</h3>
                  <p className="mt-1 text-sm leading-6 text-zinc-600">{error}</p>
                </div>
              </div>
              <button type="button" onClick={loadSessions} className="min-h-11 shrink-0 cursor-pointer rounded-lg border border-zinc-300 px-4 text-sm font-black text-zinc-800 transition-colors duration-200 hover:border-red-700 hover:text-red-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700">Thử tải lại</button>
            </section>
          ) : null}

          {loading && !sessions.length ? <LoadingSessions /> : null}

          {!loading && !error && sessions.length === 0 ? (
            <section className="overflow-hidden rounded-2xl border border-zinc-200 bg-white px-6 py-14 text-center shadow-sm sm:py-16">
              <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-zinc-100 text-zinc-600">
                <svg viewBox="0 0 24 24" className="size-7" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></svg>
              </span>
              <h3 className="mt-5 font-serif text-2xl font-bold text-zinc-950">Không có phiên nào đang mở</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-600">Khi có tài khoản đăng nhập, thông tin phiên và thời hạn Redis sẽ xuất hiện tại đây.</p>
            </section>
          ) : null}

          {sessions.length > 0 ? (
            <ul aria-label="Danh sách phiên đăng nhập hoạt động" className="space-y-3">
              {sessions.map((session) => {
                const remaining = Number(session.expiresInSeconds) < 0
                  ? null
                  : Math.max(0, Number(session.expiresInSeconds || 0) - secondsElapsed);
                const revoking = revokingIds.has(session.sessionId);
                const ttlPercent = remaining === null ? 100 : Math.min(100, Math.max(0, (remaining / 1800) * 100));
                const ttlTone = remaining !== null && remaining <= 60 ? 'text-red-700' : 'text-zinc-950';
                return (
                  <li key={session.sessionId}>
                    <article aria-label={`Phiên của ${session.username}`} className="group rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-zinc-300 hover:shadow-md motion-reduce:transform-none motion-reduce:transition-none sm:p-5 lg:p-6">
                      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,2fr)_auto] lg:items-center lg:gap-7">
                        <div className="flex min-w-0 items-center gap-3.5">
                          <span aria-hidden="true" className={`grid size-12 shrink-0 place-items-center rounded-2xl text-sm font-black tracking-wide ${session.isCurrent ? 'bg-red-700 text-white shadow-lg shadow-red-900/15' : 'bg-zinc-950 text-zinc-100'}`}>
                            {getInitials(session.username)}
                          </span>
                          <div className="min-w-0">
                            <h3 className="truncate text-base font-black text-zinc-950 sm:text-lg">{session.username}</h3>
                            <div className="mt-1.5 flex flex-wrap items-center gap-2">
                              <span className="rounded-md bg-zinc-100 px-2 py-1 text-[11px] font-bold text-zinc-600">{session.role}</span>
                              {session.isCurrent ? <span className="rounded-md bg-red-50 px-2 py-1 text-[11px] font-bold text-red-800">Phiên hiện tại</span> : null}
                            </div>
                          </div>
                        </div>

                        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-y border-zinc-100 py-4 sm:grid-cols-3 sm:gap-4 lg:border-y-0 lg:py-0">
                          <div className="min-w-0">
                            <dt className="text-[11px] font-black uppercase tracking-wider text-zinc-500">Đăng nhập</dt>
                            <dd className="mt-1.5 text-sm font-semibold tabular-nums text-zinc-800">{formatDate(session.loginAt)}</dd>
                          </div>
                          <div className="min-w-0">
                            <dt className="text-[11px] font-black uppercase tracking-wider text-zinc-500">Hoạt động gần nhất</dt>
                            <dd className="mt-1.5 text-sm font-semibold tabular-nums text-zinc-800">{formatDate(session.lastActive)}</dd>
                          </div>
                          <div className="col-span-2 min-w-0 sm:col-span-1">
                            <dt className="text-[11px] font-black uppercase tracking-wider text-zinc-500">TTL còn lại</dt>
                            <dd className={`mt-1.5 text-sm font-black tabular-nums ${ttlTone}`} aria-label={remaining === null ? 'Không giới hạn TTL' : `Còn ${formatDuration(remaining)}`}>
                              {remaining === null ? 'Không giới hạn' : formatDuration(remaining)}
                            </dd>
                            {remaining !== null ? <div className="mt-2 h-1 overflow-hidden rounded-full bg-zinc-100"><span className={`block h-full rounded-full transition-[width] duration-300 ${remaining <= 60 ? 'bg-red-700' : 'bg-emerald-600'}`} style={{ width: `${ttlPercent}%` }} /></div> : null}
                          </div>
                        </dl>

                        <div className="flex items-center justify-between gap-3 border-t border-zinc-100 pt-3 lg:justify-end lg:border-0 lg:pt-0">
                          {session.isCurrent ? (
                            <span className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-zinc-500">
                              <svg viewBox="0 0 24 24" className="size-4 text-emerald-700" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>
                              Phiên đang dùng
                            </span>
                          ) : (
                            <button type="button" aria-label={`Thu hồi phiên của ${session.username}`} aria-busy={revoking} disabled={revoking} onClick={() => handleRevoke(session)} className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border border-red-200 px-3.5 text-sm font-bold text-red-800 transition-colors duration-200 hover:border-red-700 hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:cursor-wait disabled:opacity-60">
                              {revoking ? <span className="size-3.5 animate-spin rounded-full border-2 border-red-200 border-t-red-700 motion-reduce:animate-none" aria-hidden="true" /> : <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M10 17l5-5-5-5M15 12H3" /><path d="M12 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" /></svg>}
                              {revoking ? 'Đang thu hồi...' : 'Thu hồi phiên'}
                            </button>
                          )}
                        </div>
                      </div>
                    </article>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  );
}
