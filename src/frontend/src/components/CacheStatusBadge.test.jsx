import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import CacheStatusBadge from './CacheStatusBadge';

describe('CacheStatusBadge', () => {
  it.each(['HIT', 'MISS', 'UNKNOWN'])('hiện trạng thái %s và thời gian GET', (status) => {
    render(<CacheStatusBadge cacheInfo={{ status, durationMs: 25.4 }} />);
    expect(screen.getByRole('status', { name: 'Thông tin cache bài viết' })).toHaveTextContent(`CACHE ${status}`);
    expect(screen.getByText('Phản hồi GET: 25,4 ms')).toBeInTheDocument();
    expect(screen.getByText(/Đo tại trình duyệt; không phải thời gian xử lý riêng của Redis/)).toBeInTheDocument();
  });

  it.each([null, undefined, {}, { status: '<img src=x onerror=alert(1)>', durationMs: 2 }])(
    'metadata thiếu/lạ %j không hiện raw header', (cacheInfo) => {
      render(<CacheStatusBadge cacheInfo={cacheInfo} />);
      expect(screen.getByText('CACHE UNKNOWN')).toBeInTheDocument();
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    },
  );

  it.each([null, undefined, NaN, Infinity, -1, '5'])('duration %s không hiển thị số giả', (durationMs) => {
    render(<CacheStatusBadge cacheInfo={{ status: 'HIT', durationMs }} />);
    expect(screen.getByText('Chưa đo được thời gian')).toBeInTheDocument();
  });

  it('chấp nhận 0 ms, không suy luận trạng thái từ thời gian', () => {
    const { rerender } = render(<CacheStatusBadge cacheInfo={{ status: 'MISS', durationMs: 0 }} />);
    expect(screen.getByText('CACHE MISS')).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 0,0 ms')).toBeInTheDocument();
    rerender(<CacheStatusBadge cacheInfo={{ status: 'HIT', durationMs: 900 }} />);
    expect(screen.getByText('CACHE HIT')).toBeInTheDocument();
    expect(screen.getByText('Phản hồi GET: 900,0 ms')).toBeInTheDocument();
  });
});
