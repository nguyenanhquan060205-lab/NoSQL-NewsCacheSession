import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { authApi } from '../services/api';
import { getApiMessage, getApiStatus } from '../utils/apiError';
import AuthContext from './authContextValue';
let pendingMeRequest = null;

function getMeOnce(force = false) {
  if (pendingMeRequest && !force) return pendingMeRequest;

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

  const refresh = useCallback(async ({ silent = false, force = false } = {}) => {
    const generation = ++generationRef.current;
    if (!silent) setStatus('loading');
    setError('');

    try {
      const response = await getMeOnce(force);
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
    const generation = ++generationRef.current;

    getMeOnce()
      .then((response) => {
        if (generation !== generationRef.current) return;
        setUser(response.data);
        setStatus('authenticated');
      })
      .catch((requestError) => {
        if (generation !== generationRef.current) return;
        setUser(null);
        if (getApiStatus(requestError) === 401) {
          setStatus('unauthenticated');
          setError('');
        } else {
          setStatus('error');
          setError(getApiMessage(requestError, 'Không thể kiểm tra phiên đăng nhập. Vui lòng thử lại.'));
        }
      });

    return () => { generationRef.current += 1; };
  }, []);

  const value = useMemo(() => ({ user, status, error, refresh, clearAuth }), [clearAuth, error, refresh, status, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
