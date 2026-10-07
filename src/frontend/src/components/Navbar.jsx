import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authApi, categoriesApi } from '../services/api';
import { useAuth } from '../context/useAuth';
import { getApiMessage } from '../utils/apiError';

function getVietnameseDate() {
  const formattedDate = new Intl.DateTimeFormat('vi-VN', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date());

  return formattedDate.charAt(0).toUpperCase() + formattedDate.slice(1);
}

export default function Navbar() {
  const { user, clearAuth } = useAuth();
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [logoutError, setLogoutError] = useState('');
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const logoutInProgress = useRef(false);
  const selectedCategoryId = new URLSearchParams(search).get('categoryId') || '';
  const isHome = pathname === '/';

  const handleLogout = async () => {
    if (logoutInProgress.current) return;
    logoutInProgress.current = true;
    setIsLoggingOut(true);
    setLogoutError('');

    try {
      await authApi.logout();
      clearAuth();
      navigate('/', { replace: true });
    } catch (error) {
      setLogoutError(getApiMessage(error, 'Không thể đăng xuất lúc này. Vui lòng thử lại.'));
    } finally {
      logoutInProgress.current = false;
      setIsLoggingOut(false);
    }
  };

  useEffect(() => {
    let active = true;

    categoriesApi.getAll()
      .then((response) => {
        if (active) {
          setCategories(Array.isArray(response.data) ? response.data : []);
        }
      })
      .catch(() => {
        if (active) setCategories([]);
      });

    return () => { active = false; };
  }, []);

  return (
    <header className="bg-white">
      <div className="border-b border-zinc-200 bg-zinc-50">
        <div className="mx-auto flex min-h-9 max-w-7xl items-center justify-between gap-4 px-4 text-xs text-zinc-600 sm:px-6 lg:px-8">
          <p className="whitespace-nowrap">{getVietnameseDate()}</p>
          <div className="flex items-center gap-4">
            <a href="/#tin-moi" className="hidden min-h-9 items-center font-semibold transition-colors hover:text-red-700 sm:inline-flex">
              Tin mới nhất
            </a>
            <span className="hidden h-3 w-px bg-zinc-300 sm:block" aria-hidden="true" />
            <span className="inline-flex min-h-9 items-center gap-1.5 font-semibold">
              <span className="inline-flex size-2 rounded-full bg-red-700" aria-hidden="true" />
              Redis Cache-Aside
            </span>
          </div>
        </div>
      </div>

      <div className="border-b border-zinc-200">
        <div className="relative mx-auto grid min-h-20 max-w-7xl grid-cols-[1fr_auto] items-center gap-4 px-4 sm:min-h-24 sm:px-6 md:grid-cols-[1fr_auto_1fr] lg:px-8">
          <div className="hidden text-xs leading-5 text-zinc-500 md:block">
            <p className="font-bold uppercase tracking-[0.14em] text-red-700">Chuyên trang tin tức</p>
            <p>Nhanh hơn với Redis Cache</p>
          </div>

          <Link to="/" className="group inline-flex min-h-12 items-center" aria-label="NewsCache - Trang chủ">
            <span className="font-editorial text-[1.85rem] font-black leading-none tracking-[-0.06em] text-zinc-950 sm:text-[2.5rem]">
              NEWS<span className="text-red-700">CACHE</span>
            </span>
          </Link>

          <div className="flex items-center justify-end gap-1 sm:gap-2">
            {user?.role === 'admin' ? (
              <Link
                to="/admin/posts"
                aria-label="Quản trị bài viết"
                className="inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-bold text-zinc-700 transition-colors hover:bg-zinc-100 hover:text-red-700"
              >
                <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                  <path d="M4 5h16M4 12h16M4 19h16" />
                  <circle cx="8" cy="5" r="1.5" fill="currentColor" stroke="none" />
                  <circle cx="16" cy="12" r="1.5" fill="currentColor" stroke="none" />
                  <circle cx="10" cy="19" r="1.5" fill="currentColor" stroke="none" />
                </svg>
                <span className="hidden lg:inline">Quản trị bài viết</span>
                <span className="lg:hidden">Quản trị</span>
              </Link>
            ) : null}
            <Link
              to="/posts/new"
              className="hidden min-h-11 items-center gap-2 rounded-md px-3 text-sm font-bold text-zinc-700 transition-colors hover:bg-zinc-100 hover:text-red-700 sm:inline-flex"
            >
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" />
              </svg>
              Viết bài
            </Link>
            {user ? (
              <>
                <span className="hidden max-w-32 truncate text-sm font-semibold text-zinc-600 xl:inline" title={user.username}>
                  {user.username}
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="inline-flex min-h-11 items-center rounded-md border border-zinc-300 px-3 text-sm font-bold text-zinc-800 transition-colors hover:border-red-700 hover:text-red-700 disabled:cursor-wait disabled:opacity-60"
                >
                  {isLoggingOut ? 'Đang đăng xuất…' : 'Đăng xuất'}
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="inline-flex min-h-11 items-center gap-2 rounded-md border border-zinc-300 px-3 text-sm font-bold text-zinc-800 transition-colors hover:border-red-700 hover:text-red-700"
              >
                <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
                </svg>
                <span className="hidden sm:inline">Đăng nhập</span>
                <span className="sm:hidden">Tài khoản</span>
              </Link>
            )}
          </div>
          {logoutError ? <p role="alert" className="absolute right-4 top-full z-20 mt-1 max-w-sm border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800 shadow-sm">{logoutError}</p> : null}
        </div>
      </div>

      <nav aria-label="Chuyên mục" className="border-b border-zinc-300 border-t-2 border-t-red-700 bg-white shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
        <div className="news-nav-scrollbar mx-auto flex max-w-7xl overflow-x-auto px-2 sm:px-4 lg:px-6">
          <Link
            to={{ pathname: '/', hash: '#tin-moi' }}
            aria-current={isHome && !selectedCategoryId ? 'page' : undefined}
            className={`inline-flex min-h-11 shrink-0 items-center justify-center border-b-2 px-3 transition-colors ${
              isHome && !selectedCategoryId
                ? 'border-red-700 text-red-700'
                : 'border-transparent text-zinc-600 hover:border-zinc-300 hover:text-zinc-950'
            }`}
            aria-label="Tất cả tin tức"
          >
            <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="m3 11 9-8 9 8" />
              <path d="M5.5 9.5V21h13V9.5M9.5 21v-7h5v7" />
            </svg>
          </Link>
          {categories.map((category) => (
            <Link
              key={category.id}
              to={{ pathname: '/', search: `?categoryId=${encodeURIComponent(category.id)}`, hash: '#tin-moi' }}
              aria-current={isHome && selectedCategoryId === category.id ? 'page' : undefined}
              className={`inline-flex min-h-11 shrink-0 items-center border-b-2 px-3 text-sm font-bold transition-colors ${
                isHome && selectedCategoryId === category.id
                  ? 'border-red-700 text-red-700'
                  : 'border-transparent text-zinc-700 hover:border-red-700 hover:text-red-700'
              }`}
            >
              {category.name}
            </Link>
          ))}
          <Link
            to={{ pathname: '/', search, hash: '#doc-nhieu' }}
            className="inline-flex min-h-11 shrink-0 items-center border-b-2 border-transparent px-3 text-sm font-bold text-zinc-700 transition-colors hover:border-red-700 hover:text-red-700"
          >
            Đọc nhiều
          </Link>
        </div>
      </nav>
    </header>
  );
}
