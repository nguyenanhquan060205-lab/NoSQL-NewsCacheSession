// TODO [SV3]: Trang chi tiết bài viết — ĐÂY LÀ TRANG DEMO CACHE-ASIDE
// ⭐ Lần 1 load: Cache Miss → response chậm (~200ms)
// ⭐ Lần 2 load: Cache Hit → response nhanh (<5ms)
//
// 1. useEffect → gọi postsApi.getById(id)
// 2. Đo thời gian response (performance.now()) để demo
// 3. Gọi postsApi.incrementView(id) khi mount (INCR lượt xem)
// 4. Hiển thị nút Sửa/Xóa nếu là tác giả

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { postsApi } from '../services/api';

export default function PostDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [responseTime, setResponseTime] = useState(null);

  useEffect(() => {
    // TODO [SV3]: Fetch bài viết + đo thời gian response
    // const start = performance.now();
    // postsApi.getById(id)
    //   .then(res => {
    //     setPost(res.data);
    //     setResponseTime((performance.now() - start).toFixed(2));
    //   })
    //   .catch(() => navigate('/'))
    //   .finally(() => setLoading(false));
    //
    // // Tăng lượt xem
    // postsApi.incrementView(id);
    setLoading(false);
  }, [id]);

  if (loading) return <p className="text-center py-8">Đang tải...</p>;
  if (!post) return <p className="text-center py-8">Bài viết không tồn tại.</p>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <article>
        <h1 className="text-3xl font-bold text-gray-800">{post.title}</h1>

        {/* Thông tin meta + thời gian response (demo Cache-Aside) */}
        <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
          <span>{new Date(post.createdAt).toLocaleDateString('vi-VN')}</span>
          <span>👁 {post.views} lượt xem</span>
          {responseTime && (
            <span className={`font-mono px-2 py-1 rounded text-xs ${
              responseTime < 20 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
            }`}>
              ⏱ {responseTime}ms {responseTime < 20 ? '(Cache Hit ⚡)' : '(Cache Miss 🐌)'}
            </span>
          )}
        </div>

        {/* Ảnh bài viết */}
        {post.imageUrl && (
          <img
            src={post.imageUrl}
            alt={post.title}
            className="w-full rounded-lg mt-6 max-h-96 object-cover"
          />
        )}

        {/* Nội dung bài viết */}
        <div className="prose max-w-none mt-6 text-gray-700 leading-relaxed">
          {post.content}
        </div>
      </article>

      {/* TODO [SV3]: Nút Sửa / Xóa (chỉ hiện nếu là tác giả) */}
      <div className="mt-8 flex gap-3">
        {/* <button className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600">
          ✏️ Sửa bài viết
        </button>
        <button className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">
          🗑️ Xóa bài viết
        </button> */}
      </div>
    </div>
  );
}
