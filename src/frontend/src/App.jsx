import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import PostDetailPage from './pages/PostDetailPage';
import CreateEditPostPage from './pages/CreateEditPostPage';
import Footer from './components/Footer';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-dvh flex-col text-zinc-900">
        <a
          href="#main-content"
          className="sr-only fixed left-4 top-4 z-[100] rounded-lg bg-zinc-950 px-4 py-3 font-bold text-white focus:not-sr-only"
        >
          Chuyển đến nội dung chính
        </a>
        <Navbar />
        <main id="main-content" className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/posts/:id" element={<PostDetailPage />} />
            <Route path="/posts/new" element={<CreateEditPostPage />} />
            <Route path="/posts/:id/edit" element={<CreateEditPostPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
