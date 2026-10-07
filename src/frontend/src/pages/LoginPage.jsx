import { useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { authApi } from '../services/api';
import { getApiMessage } from '../utils/apiError';

function getSafeReturnLocation(from) {
  const pathname = from?.pathname;
  if (typeof pathname !== 'string' || !pathname.startsWith('/') || pathname.startsWith('//') || pathname.includes('\\')) {
    return '/';
  }

  return {
    pathname,
    search: typeof from.search === 'string' ? from.search : '',
    hash: typeof from.hash === 'string' ? from.hash : '',
  };
}

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const { refresh } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submittingRef.current) return;

    submittingRef.current = true;
    setIsSubmitting(true);
    setError('');
    setNotice('');
    const normalizedUsername = username.trim();

    try {
      if (isRegister) {
        await authApi.register(normalizedUsername, password);
        setUsername(normalizedUsername);
        setPassword('');
        setIsRegister(false);
        setNotice('Tài khoản đã tạo. Đăng nhập để tiếp tục.');
        return;
      }

      await authApi.login(normalizedUsername, password);
      const authenticatedUser = await refresh({ force: true });
      if (!authenticatedUser) {
        setError('Đăng nhập thành công nhưng chưa thể tải thông tin phiên. Vui lòng thử lại.');
        return;
      }

      navigate(getSafeReturnLocation(location.state?.from), { replace: true });
    } catch (requestError) {
      setError(getApiMessage(requestError, isRegister
        ? 'Không thể tạo tài khoản lúc này. Vui lòng thử lại.'
        : 'Không thể đăng nhập lúc này. Vui lòng thử lại.'));
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  const switchMode = () => {
    setIsRegister((current) => !current);
    setError('');
    setNotice('');
  };

  return (
    <main className="min-h-[70vh] bg-zinc-50 px-4 py-12 sm:px-6 sm:py-16">
      <div className="mx-auto grid w-full max-w-5xl overflow-hidden border border-zinc-200 bg-white shadow-sm md:grid-cols-[0.9fr_1.1fr]">
        <aside className="flex flex-col justify-between bg-zinc-950 p-7 text-white sm:p-10">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-red-400">NewsCache · Tài khoản</p>
            <h1 className="mt-8 font-editorial text-4xl font-black leading-tight tracking-tight sm:text-5xl">
              Tin tức đáng tin, bắt đầu từ đây.
            </h1>
            <p className="mt-5 max-w-sm text-sm leading-6 text-zinc-300">
              Đăng nhập để tiếp tục viết bài và quản lý nội dung trên NewsCache.
            </p>
          </div>
          <Link to="/" className="mt-10 inline-flex min-h-11 items-center self-start text-sm font-semibold text-zinc-300 underline decoration-zinc-600 underline-offset-4 transition hover:text-white">
            ← Quay về trang chủ
          </Link>
        </aside>

        <section className="p-6 sm:p-10 lg:p-12" aria-labelledby="auth-heading">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-red-700">Chào mừng bạn</p>
          <h2 id="auth-heading" className="mt-2 font-editorial text-3xl font-black tracking-tight text-zinc-950">
            {isRegister ? 'Tạo tài khoản' : 'Đăng nhập'}
          </h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600">
            {isRegister ? 'Tạo tài khoản mới để tham gia đóng góp nội dung.' : 'Nhập thông tin tài khoản để tiếp tục.'}
          </p>

          {isRegister ? (
            <p className="mt-5 border-l-2 border-red-700 bg-red-50 px-3 py-2 text-xs leading-5 text-zinc-700">
              Tài khoản đầu tiên trên hệ thống sẽ được cấp quyền quản trị.
            </p>
          ) : null}

          {notice ? <p role="status" className="mt-5 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{notice}</p> : null}
          {error ? <p role="alert" className="mt-5 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
            <div>
              <label htmlFor="username" className="mb-2 block text-sm font-bold text-zinc-800">Tên đăng nhập</label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="min-h-12 w-full border border-zinc-300 bg-white px-3 text-base text-zinc-950 outline-none transition placeholder:text-zinc-400 focus:border-red-700 focus:ring-2 focus:ring-red-700/20"
                required
                disabled={isSubmitting}
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-bold text-zinc-800">Mật khẩu</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="min-h-12 w-full border border-zinc-300 bg-white px-3 text-base text-zinc-950 outline-none transition placeholder:text-zinc-400 focus:border-red-700 focus:ring-2 focus:ring-red-700/20"
                required
                minLength={isRegister ? 6 : undefined}
                disabled={isSubmitting}
              />
              {isRegister ? <p className="mt-2 text-xs text-zinc-500">Mật khẩu cần có ít nhất 6 ký tự.</p> : null}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex min-h-12 w-full items-center justify-center bg-red-700 px-4 text-sm font-bold text-white transition hover:bg-red-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:cursor-wait disabled:opacity-60"
            >
              {isSubmitting ? 'Đang xử lý…' : isRegister ? 'Tạo tài khoản' : 'Đăng nhập'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-zinc-600">
            {isRegister ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'}{' '}
            <button
              type="button"
              onClick={switchMode}
              disabled={isSubmitting}
              aria-label={`${isRegister ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'} ${isRegister ? 'Đăng nhập' : 'Đăng ký'}`}
              className="min-h-11 px-1 font-bold text-red-700 underline underline-offset-4 hover:text-red-800 disabled:opacity-60"
            >
              {isRegister ? 'Đăng nhập' : 'Đăng ký'}
            </button>
          </p>
        </section>
      </div>
    </main>
  );
}
