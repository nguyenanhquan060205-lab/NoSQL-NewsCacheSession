import { describe, expect, it, vi } from 'vitest';
import { parsePostLink, runBatch, summarizeRounds } from './benchmark';

describe('Đọc link bài viết', () => {
  it('lấy ID từ link chi tiết, link sửa bài hoặc ID trần', () => {
    expect(parsePostLink('http://localhost:3000/posts/6AC6BF1B5CDEE79754D461F0')).toEqual({ id: '6ac6bf1b5cdee79754d461f0' });
    expect(parsePostLink('/posts/6ac6bf1b5cdee79754d461f0/edit')).toEqual({ id: '6ac6bf1b5cdee79754d461f0' });
    expect(parsePostLink(' 6ac6bf1b5cdee79754d461f0 ')).toEqual({ id: '6ac6bf1b5cdee79754d461f0' });
  });
  it('lấy slug khi link không có ID', () => {
    expect(parsePostLink('http://localhost:5134/api/posts/slug/tin-mau-000001')).toEqual({ slug: 'tin-mau-000001' });
    expect(parsePostLink('tin-mau-000001')).toEqual({ slug: 'tin-mau-000001' });
  });
  it('từ chối nội dung không phải link bài viết', () => {
    expect(parsePostLink('')).toBeNull();
    expect(parsePostLink('   ')).toBeNull();
    expect(parsePostLink('http://localhost:3000/')).toBeNull();
    expect(parsePostLink('không phải link')).toBeNull();
  });
});

describe('Chạy một đợt request', () => {
  it('đếm HIT, MISS, lỗi và báo tiến độ sau mỗi request', async () => {
    const statuses = ['MISS', 'HIT', 'HIT'];
    const request = vi.fn(async () => {
      const status = statuses.shift();
      if (!status) throw new Error('boom');
      return status;
    });
    const onProgress = vi.fn();

    const run = await runBatch({ request, count: 4, onProgress });

    expect(run).toMatchObject({ count: 4, hit: 2, miss: 1, errors: 1 });
    expect(run.latencies).toHaveLength(4);
    expect(run.totalMs).toBeGreaterThanOrEqual(0);
    expect(onProgress).toHaveBeenCalledTimes(4);
    expect(onProgress.mock.lastCall[0].done).toBe(4);
  });
  it('dừng giữa chừng khi được yêu cầu', async () => {
    let calls = 0;
    const run = await runBatch({ request: async () => { calls += 1; return 'HIT'; }, count: 10, shouldStop: () => calls >= 3 });
    expect(run.count).toBe(3);
  });
});

describe('Tính trung bình các lần đo', () => {
  it('chỉ tính lần đo chạy đủ và ra tỷ lệ nhanh hơn', () => {
    const summary = summarizeRounds([
      { round: 1, redis: { totalMs: 200, complete: true }, mongo: { totalMs: 600, complete: true } },
      { round: 2, redis: { totalMs: 400, complete: true }, mongo: { totalMs: 600, complete: true } },
      { round: 3, redis: { totalMs: 50, complete: false } },
    ]);
    expect(summary).toEqual({ redisAvgMs: 300, mongoAvgMs: 600, speedup: 2 });
  });
  it('trả null khi chưa có lần đo nào xong', () => {
    expect(summarizeRounds([])).toEqual({ redisAvgMs: null, mongoAvgMs: null, speedup: null });
  });
});
