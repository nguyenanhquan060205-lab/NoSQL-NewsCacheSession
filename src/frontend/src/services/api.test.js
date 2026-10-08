import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { authApi, postsApi } from './api';

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

describe('postsApi thông tin cache của GET chi tiết', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    http.get.mockResolvedValue({ data: { id: 'post-1' } });
    vi.spyOn(performance, 'now').mockReturnValueOnce(100).mockReturnValue(125.4);
  });

  afterEach(() => vi.restoreAllMocks());

  it('giữ dữ liệu và hợp đồng Axios, không mutate response', async () => {
    const response = Object.freeze({ data: { id: 'post-1' }, status: 200, headers: { 'x-cache': 'HIT' }, config: {}, request: {} });
    http.get.mockResolvedValue(response);
    const result = await postsApi.getById('post-1');

    expect(http.get).toHaveBeenCalledWith('/posts/post-1');
    for (const field of ['data', 'status', 'headers', 'config', 'request']) expect(result[field]).toBe(response[field]);
    expect(response).not.toHaveProperty('cacheInfo');
    expect(result.cacheInfo.status).toBe('HIT');
    expect(result.cacheInfo.durationMs).toBeCloseTo(25.4);
  });

  it.each([
    [{ 'x-cache': 'HIT' }, 'HIT'],
    [{ 'X-Cache': ' miss ' }, 'MISS'],
    [{ 'x-cache': 'hit' }, 'HIT'],
    [undefined, 'UNKNOWN'],
    [{}, 'UNKNOWN'],
    [{ 'x-cache': '<script>HIT</script>' }, 'UNKNOWN'],
    [{ 'x-cache': ['HIT', 'MISS'] }, 'UNKNOWN'],
    [{ 'x-cache': true }, 'UNKNOWN'],
  ])('chuẩn hóa header %j thành %s', async (headers, status) => {
    http.get.mockResolvedValue({ data: {}, headers });
    expect((await postsApi.getById('post-1')).cacheInfo.status).toBe(status);
  });

  it('đọc AxiosHeaders thật dù HTTP client được mock', async () => {
    const { AxiosHeaders } = await vi.importActual('axios');
    http.get.mockResolvedValue({ data: {}, headers: new AxiosHeaders({ 'X-Cache': 'MISS' }) });
    expect((await postsApi.getById('post-1')).cacheInfo.status).toBe('MISS');
  });

  it.each([404, 500, undefined])('giữ nguyên rejection của request %s', async (status) => {
    const error = status ? { response: { status } } : new Error('Mất kết nối');
    http.get.mockRejectedValue(error);
    await expect(postsApi.getById('post-1')).rejects.toBe(error);
  });

  it.each([[100, 100, 0], [100, 99, null], [NaN, 110, null], [100, Infinity, null], [-Number.MAX_VALUE, Number.MAX_VALUE, null]])(
    'xử lý timestamp %s → %s', async (start, end, expected) => {
      performance.now.mockReset().mockReturnValueOnce(start).mockReturnValue(end);
      expect((await postsApi.getById('post-1')).cacheInfo.durationMs).toBe(expected);
    },
  );

  it('clock lỗi không làm lỗi việc đọc bài', async () => {
    performance.now.mockImplementation(() => { throw new Error('Không có clock'); });
    const result = await postsApi.getById('post-1');
    expect(result.data.id).toBe('post-1');
    expect(result.cacheInfo.durationMs).toBeNull();
  });

  it('header getter lỗi không làm lỗi việc đọc bài', async () => {
    http.get.mockResolvedValue({ data: {}, headers: { get: () => { throw new Error('Không đọc được header'); } } });
    expect((await postsApi.getById('post-1')).cacheInfo.status).toBe('UNKNOWN');
  });

  it('gắn timing riêng cho hai request resolve đảo thứ tự', async () => {
    let resolveFirst;
    let resolveSecond;
    http.get.mockReturnValueOnce(new Promise((resolve) => { resolveFirst = resolve; }))
      .mockReturnValueOnce(new Promise((resolve) => { resolveSecond = resolve; }));
    performance.now.mockReset().mockReturnValueOnce(10).mockReturnValueOnce(20)
      .mockReturnValueOnce(25).mockReturnValueOnce(50);
    const first = postsApi.getById('first');
    const second = postsApi.getById('second');
    resolveSecond({ data: { id: 'second' }, headers: { 'x-cache': 'HIT' } });
    expect((await second).cacheInfo.durationMs).toBe(5);
    resolveFirst({ data: { id: 'first' }, headers: { 'x-cache': 'MISS' } });
    expect((await first).cacheInfo.durationMs).toBe(40);
  });

  it('không gắn telemetry vào danh sách, auth hay tăng lượt xem', async () => {
    const response = { data: {} };
    http.get.mockResolvedValue(response);
    http.post.mockResolvedValue(response);
    expect(await postsApi.getAll(1, 12)).toBe(response);
    expect(await authApi.getMe()).toBe(response);
    expect(await postsApi.incrementView('post-1')).toBe(response);
    expect(response).not.toHaveProperty('cacheInfo');
  });
});
