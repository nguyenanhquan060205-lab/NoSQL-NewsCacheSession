import { Link } from 'react-router-dom';

// TODO [SV3]: Component hiển thị 1 card bài viết trong danh sách
// Props: { id, title, content, imageUrl, views, createdAt }
// - Hiển thị thumbnail (imageUrl), tiêu đề, mô tả ngắn (content cắt 100 ký tự)
// - Hiển thị lượt xem (views) và ngày đăng (createdAt)
// - Click → navigate tới /posts/:id

export default function PostCard({ post }) {
  return (
    <Link
      to={`/posts/${post.id}`}
      className="block bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"
    >
      {/* TODO [SV3]: Hiển thị ảnh thumbnail */}
      {post.imageUrl && (
        <img
          src={post.imageUrl}
          alt={post.title}
          className="w-full h-48 object-cover"
        />
      )}
      <div className="p-4">
        <h2 className="text-lg font-semibold text-gray-800 line-clamp-2">
          {post.title}
        </h2>
        <p className="text-gray-500 text-sm mt-2 line-clamp-2">
          {post.content}
        </p>
        <div className="flex items-center justify-between mt-3 text-xs text-gray-400">
          <span>👁 {post.views} lượt xem</span>
          <span>{new Date(post.createdAt).toLocaleDateString('vi-VN')}</span>
        </div>
      </div>
    </Link>
  );
}
