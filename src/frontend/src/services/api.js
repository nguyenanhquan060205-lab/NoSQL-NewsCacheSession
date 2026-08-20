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
};

// ========== POSTS API ==========

export const postsApi = {
  // TODO [SV3]: Gọi GET /api/posts?page=&pageSize=
  getAll: (page = 1, pageSize = 10) =>
    api.get('/posts', { params: { page, pageSize } }),

  // TODO [SV3]: Gọi GET /api/posts/:id — ĐÂY LÀ ENDPOINT CACHE-ASIDE
  getById: (id) =>
    api.get(`/posts/${id}`),

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

export default api;
