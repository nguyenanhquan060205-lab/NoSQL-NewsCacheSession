import { beforeEach, describe, expect, it, vi } from 'vitest';
import { authApi } from './api';

const { http } = vi.hoisted(() => ({ http: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
vi.mock('axios', () => ({ default: { create: vi.fn(() => http) } }));

describe('authApi session endpoints', () => {
  beforeEach(() => {
    http.get.mockClear();
    http.delete.mockClear();
  });

  it('gets active sessions from the auth endpoint', () => {
    authApi.getActiveSessions();

    expect(http.get).toHaveBeenCalledWith('/auth/sessions');
  });

  it('encodes the session id before sending a revoke request', () => {
    authApi.revokeSession('session /?1');

    expect(http.delete).toHaveBeenCalledWith('/auth/sessions/session%20%2F%3F1');
  });
});
