import axios from 'axios';

// Base URL — Vite proxy sẽ chuyển /api/* tới backend
const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

// ========== AUTH API ==========

export const authApi = {
  // TODO [SV3]: Gọi POST /api/auth/register
  register: (username, password) =>
    api.post('/auth/register', { username, password }),

  // TODO [SV3]: Gọi POST /api/auth/login
  login: (username, password) =>
    api.post('/auth/login', { username, password }),

  // TODO [SV3]: Gọi POST /api/auth/logout
  logout: () =>
    api.post('/auth/logout'),

  // TODO [SV3]: Gọi GET /api/auth/me
  getMe: () =>
    api.get('/auth/me'),

  getActiveSessions: () =>
    api.get('/auth/sessions'),

  revokeSession: (sessionId) =>
    api.delete(`/auth/sessions/${encodeURIComponent(sessionId)}`),
};

// ========== POSTS API ==========

function readTimestamp() {
  try {
    const value = globalThis.performance?.now();
    return Number.isFinite(value) ? value : null;
  } catch {
    return null;
  }
}

function readCacheStatus(headers) {
  try {
    const value = typeof headers?.get === 'function'
      ? headers.get('x-cache')
      : Object.entries(headers || {}).find(([name]) => name.toLowerCase() === 'x-cache')?.[1];
    const status = typeof value === 'string' ? value.trim().toUpperCase() : '';
    return status === 'HIT' || status === 'MISS' ? status : 'UNKNOWN';
  } catch {
    return 'UNKNOWN';
  }
}

export const postsApi = {
  // Danh sách có phân trang và có thể lọc theo chuyên mục.
  getAll: (page = 1, pageSize = 10, categoryId = '') =>
    api.get('/posts', {
      params: {
        page,
        pageSize,
        ...(categoryId ? { categoryId } : {}),
      },
    }),

  // Đo riêng GET thật; các subscriber dùng chung request sẽ nhận cùng metadata.
  getById: async (id) => {
    const startedAt = readTimestamp();
    const response = await api.get(`/posts/${id}`);
    const finishedAt = readTimestamp();
    const elapsed = startedAt !== null && finishedAt !== null && finishedAt >= startedAt
      ? finishedAt - startedAt
      : null;
    const durationMs = Number.isFinite(elapsed) ? elapsed : null;

    return { ...response, cacheInfo: { status: readCacheStatus(response.headers), durationMs } };
  },

  // TODO [SV3]: Gọi POST /api/posts
  create: (data) =>
    api.post('/posts', data),

  // TODO [SV3]: Gọi PUT /api/posts/:id — Trigger Cache Invalidation
  update: (id, data) =>
    api.put(`/posts/${id}`, data),

  // TODO [SV3]: Gọi DELETE /api/posts/:id — Trigger Cache Invalidation
  delete: (id) =>
    api.delete(`/posts/${id}`),

  // TODO [SV3]: Gọi POST /api/posts/:id/view — INCR lượt xem
  incrementView: (id) =>
    api.post(`/posts/${id}/view`),
};

// ========== CATEGORIES API ==========

export const categoriesApi = {
  getAll: () => api.get('/categories'),
};

export default api;
