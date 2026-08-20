// TODO [SV3]: Trang tạo / sửa bài viết
// 1. Form: Title, Content (textarea), ImageUrl
// 2. Nếu có param id → mode "Sửa" → fetch post hiện tại, fill vào form
// 3. Nếu không có id → mode "Tạo mới"
// 4. Submit:
//    - Tạo mới: postsApi.create(data) → navigate tới /posts/:id
//    - Sửa: postsApi.update(id, data) → navigate tới /posts/:id
//    - Sửa sẽ trigger Cache Invalidation ở backend

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { postsApi } from '../services/api';

export default function CreateEditPostPage() {
  const { id } = useParams(); // undefined nếu tạo mới
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [imageUrl, setImageUrl] = useState('');

  useEffect(() => {
    if (isEdit) {
      // TODO [SV3]: Fetch bài viết hiện tại để fill form
      // postsApi.getById(id).then(res => {
      //   setTitle(res.data.title);
      //   setContent(res.data.content);
      //   setImageUrl(res.data.imageUrl || '');
      // });
    }
  }, [id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    // TODO [SV3]: Implement submit
    // const data = { title, content, imageUrl };
    // if (isEdit) {
    //   await postsApi.update(id, data);
    // } else {
    //   await postsApi.create(data);
    // }
    // navigate('/');
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">
        {isEdit ? '✏️ Sửa Bài Viết' : '📝 Viết Bài Mới'}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          placeholder="Tiêu đề bài viết"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg"
          required
        />
        <textarea
          placeholder="Nội dung bài viết..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[200px]"
          required
        />
        <input
          type="url"
          placeholder="URL hình ảnh (tuỳ chọn)"
          value={imageUrl}
          onChange={(e) => setImageUrl(e.target.value)}
          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
        >
          {isEdit ? 'Cập nhật' : 'Đăng bài'}
        </button>
      </form>
    </div>
  );
}
