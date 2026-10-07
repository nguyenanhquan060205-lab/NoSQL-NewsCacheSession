import { useEffect, useState } from 'react';
import { Link, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function RequireAdmin() {
  const { user, status, error, refresh } = useAuth();
  const location = useLocation();
  const [checkingRoute, setCheckingRoute] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.resolve(refresh({ silent: true })).finally(() => {
      if (active) setCheckingRoute(false);
    });

    const revalidate = () => refresh({ silent: true });
    const revalidateWhenVisible = () => {
      if (document.visibilityState === 'visible') revalidate();
    };

    window.addEventListener('focus', revalidate);
    document.addEventListener('visibilitychange', revalidateWhenVisible);
    return () => {
      active = false;
      window.removeEventListener('focus', revalidate);
      document.removeEventListener('visibilitychange', revalidateWhenVisible);
    };
  }, [refresh]);

  if (checkingRoute || status === 'loading') {
    return (
      <div role="status" aria-live="polite" className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
        <div className="mx-auto size-9 animate-spin rounded-full border-4 border-zinc-200 border-t-red-700" aria-hidden="true" />
        <p className="mt-4 text-sm font-bold text-zinc-600">Đang kiểm tra quyền quản trị...</p>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6" aria-labelledby="auth-error-title">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-red-700">Kết nối gián đoạn</p>
        <h1 id="auth-error-title" className="font-editorial mt-3 text-3xl font-black text-zinc-950">Chưa kiểm tra được quyền truy cập</h1>
        <p role="alert" className="mt-3 text-sm leading-6 text-red-800">{error}</p>
        <button type="button" onClick={() => refresh()} className="mt-6 min-h-11 cursor-pointer rounded-lg bg-red-700 px-5 text-sm font-black text-white transition-colors hover:bg-red-800">
          Thử kiểm tra lại
        </button>
      </section>
    );
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (user?.role !== 'admin') {
    return (
      <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6" aria-labelledby="forbidden-title">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-red-700">403 · Giới hạn truy cập</p>
        <h1 id="forbidden-title" className="font-editorial mt-3 text-3xl font-black text-zinc-950 sm:text-4xl">Bạn không có quyền truy cập</h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-zinc-600">Trang quản trị bài viết chỉ dành cho tài khoản có vai trò admin.</p>
        <Link to="/" className="mt-7 inline-flex min-h-11 items-center rounded-lg bg-zinc-950 px-5 text-sm font-black text-white transition-colors hover:bg-red-700">
          Về trang chủ
        </Link>
      </section>
    );
  }

  return <Outlet />;
}
