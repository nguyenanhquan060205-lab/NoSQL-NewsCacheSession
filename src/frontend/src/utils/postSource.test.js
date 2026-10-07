import { describe, expect, it } from 'vitest';
import { getPostSource } from './postSource';

describe('Nguồn bài viết', () => {
  it('nhận diện tóm tắt RSS và link đọc toàn bài', () => {
    expect(getPostSource({ slug: 'real-vnexpress-rss-123', content: 'Nguồn:\nhttps://vnexpress.net/tin-moi-123.html' }))
      .toEqual({ label: 'VnExpress · Tóm tắt RSS', dateLabel: 'Xuất bản ngày', url: 'https://vnexpress.net/tin-moi-123.html' });
  });
  it('không tạo link đọc nguồn ngoài báo đã chọn', () => {
    expect(getPostSource({ slug: 'real-vnexpress-rss-123', content: 'https://example.com/tin-123.html' }).url).toBeUndefined();
  });
  it('giữ nhãn dữ liệu bách khoa và ngày nguồn Wikinews', () => {
    expect(getPostSource({ slug: 'real-wikipedia-vi-123' }).dateLabel).toBe('Bản dữ liệu ngày');
    expect(getPostSource({ slug: 'real-wikinews-en-123' }).dateLabel).toBe('Nguồn cập nhật ngày');
    expect(getPostSource({ slug: 'bai-tu-viet' })).toBeNull();
  });
});
