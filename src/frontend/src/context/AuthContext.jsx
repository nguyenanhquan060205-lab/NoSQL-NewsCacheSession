import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { authApi } from '../services/api';
import { getApiMessage, getApiStatus } from '../utils/apiError';

const AuthContext = createContext(null);
let pendingMeRequest = null;

function getMeOnce() {
  if (pendingMeRequest) return pendingMeRequest;

  const request = authApi.getMe();
  pendingMeRequest = request;
  request.finally(() => {
    if (pendingMeRequest === request) pendingMeRequest = null;
  }).catch(() => {});

  return request;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');
  const generationRef = useRef(0);

  const refresh = useCallback(async ({ silent = false } = {}) => {
    const generation = ++generationRef.current;
    if (!silent) setStatus('loading');
    setError('');

    try {
      const response = await getMeOnce();
      if (generation !== generationRef.current) return null;

      setUser(response.data);
      setStatus('authenticated');
      return response.data;
    } catch (requestError) {
      if (generation !== generationRef.current) return null;

      setUser(null);
      if (getApiStatus(requestError) === 401) {
        setStatus('unauthenticated');
        setError('');
      } else {
        setStatus('error');
        setError(getApiMessage(requestError, 'Không thể kiểm tra phiên đăng nhập. Vui lòng thử lại.'));
      }
      return null;
    }
  }, []);

  const clearAuth = useCallback(() => {
    generationRef.current += 1;
    pendingMeRequest = null;
    setUser(null);
    setStatus('unauthenticated');
    setError('');
  }, []);

  useEffect(() => {
    refresh();
    return () => { generationRef.current += 1; };
  }, [refresh]);

  const value = useMemo(() => ({ user, status, error, refresh, clearAuth }), [clearAuth, error, refresh, status, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth phải được dùng bên trong AuthProvider.');
  return context;
}
