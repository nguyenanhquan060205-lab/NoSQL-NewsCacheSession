export function getPostSource(post) {
  if (post?.slug?.startsWith('real-vnexpress-rss-')) {
    const url = post.content?.match(/https:\/\/vnexpress\.net\/[a-zA-Z0-9-]+-\d+\.html/)?.[0];
    return { label: 'VnExpress · Tóm tắt RSS', dateLabel: 'Xuất bản ngày', url };
  }
  if (post?.slug?.startsWith('real-wikipedia-vi-')) {
    return { label: 'Wikipedia tiếng Việt', dateLabel: 'Bản dữ liệu ngày' };
  }
  if (post?.slug?.startsWith('real-wikinews-en-')) {
    return { label: 'Wikinews · Tiếng Anh', dateLabel: 'Nguồn cập nhật ngày' };
  }
  return null;
}
