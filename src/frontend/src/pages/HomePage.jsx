// TODO [SV3]: Trang chủ — hiển thị danh sách bài viết
// 1. useEffect → gọi postsApi.getAll(page, pageSize)
// 2. Render danh sách PostCard trong grid layout
// 3. Có phân trang (Previous / Next)

import { useState, useEffect } from 'react';
import { postsApi } from '../services/api';
import PostCard from '../components/PostCard';

export default function HomePage() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO [SV3]: Fetch danh sách bài viết
    // postsApi.getAll()
    //   .then(res => setPosts(res.data))
    //   .catch(err => console.error(err))
    //   .finally(() => setLoading(false));
    setLoading(false);
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Tin Tức Mới Nhất</h1>

      {loading ? (
        <p className="text-gray-500">Đang tải bài viết...</p>
      ) : posts.length === 0 ? (
        <p className="text-gray-500">Chưa có bài viết nào.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}

      {/* TODO [SV3]: Thêm phân trang */}
    </div>
  );
}
