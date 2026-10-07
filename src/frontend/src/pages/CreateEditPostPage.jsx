import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { categoriesApi, postsApi } from '../services/api';
import { getApiMessage, getApiStatus, getValidationErrors } from '../utils/apiError';

const EMPTY_FORM = { title: '', content: '', imageUrl: '', categoryId: '' };

function readDraft(key) {
  try {
    const value = window.sessionStorage.getItem(key);
    if (!value) return null;
    const draft = JSON.parse(value);
    return {
      title: typeof draft.title === 'string' ? draft.title : '',
      content: typeof draft.content === 'string' ? draft.content : '',
      imageUrl: typeof draft.imageUrl === 'string' ? draft.imageUrl : '',
      categoryId: typeof draft.categoryId === 'string' ? draft.categoryId : '',
    };
  } catch {
    return null;
  }
}

function writeDraft(key, form) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(form));
  } catch {
    // sessionStorage có thể bị chặn; vẫn giữ dữ liệu trong state hiện tại.
  }
}

function clearDraft(key) {
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Không chặn luồng lưu bài nếu browser không cho truy cập storage.
  }
}

function normalizePostPayload(form) {
  return {
    title: form.title.trim(),
    content: form.content.trim(),
    imageUrl: form.imageUrl.trim() || null,
    categoryId: form.categoryId || null,
  };
}

function isValidImageUrl(value) {
  if (!value) return true;
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

export default function CreateEditPostPage() {
  const { id } = useParams();
  const { clearAuth } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isEdit = Boolean(id);
  const draftKey = `scrum29:post-draft:${isEdit ? `edit:${id}` : 'create'}`;
  const initialDraft = !isEdit ? readDraft(draftKey) : null;
  const [form, setForm] = useState(initialDraft || EMPTY_FORM);
  const [categories, setCategories] = useState([]);
  const [categoryError, setCategoryError] = useState('');
  const [categoryVersion, setCategoryVersion] = useState(0);
  const [loadedPostRequestKey, setLoadedPostRequestKey] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [postVersion, setPostVersion] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [draftRestored, setDraftRestored] = useState(Boolean(initialDraft));
  const submitLockRef = useRef(false);
  const postGenerationRef = useRef(0);
  const loadedPostRef = useRef(null);
  const postRequestKey = `${id || 'new'}:${postVersion}`;
  const loadingPost = isEdit && loadedPostRequestKey !== postRequestKey;

  useEffect(() => {
    let active = true;

    categoriesApi.getAll()
      .then((response) => {
        if (!active) return;
        setCategories(Array.isArray(response.data) ? response.data : []);
        setCategoryError('');
      })
      .catch((requestError) => {
        if (!active) return;
        setCategories([]);
        setCategoryError(getApiMessage(requestError, 'Không tải được danh sách chuyên mục.'));
      });

    return () => { active = false; };
  }, [categoryVersion]);

  useEffect(() => {
    if (!isEdit) return undefined;

    const generation = ++postGenerationRef.current;
    let active = true;

    postsApi.getById(id)
      .then((response) => {
        if (!active || generation !== postGenerationRef.current) return;
        const postForm = {
          title: response.data?.title || '',
          content: response.data?.content || '',
          imageUrl: response.data?.imageUrl || '',
          categoryId: response.data?.categoryId || '',
        };
        loadedPostRef.current = postForm;
        const draft = readDraft(draftKey);
        setForm(draft || postForm);
        setDraftRestored(Boolean(draft));
        setLoadError('');
      })
      .catch((requestError) => {
        if (!active || generation !== postGenerationRef.current) return;
        setLoadError(getApiMessage(requestError, 'Không thể tải bài viết cần chỉnh sửa.'));
      })
      .finally(() => {
        if (active && generation === postGenerationRef.current) setLoadedPostRequestKey(postRequestKey);
      });

    return () => { active = false; };
  }, [draftKey, id, isEdit, postRequestKey]);

  const updateField = (field) => (event) => {
    const value = event.target.value;
    setForm((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => ({ ...current, [field]: '' }));
    setSubmitError('');
  };

  const discardDraft = () => {
    clearDraft(draftKey);
    const nextForm = isEdit ? (loadedPostRef.current || EMPTY_FORM) : EMPTY_FORM;
    setForm({ ...nextForm });
    setDraftRestored(false);
    setFieldErrors({});
    setSubmitError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitLockRef.current) return;

    const payload = normalizePostPayload(form);
    const nextFieldErrors = {};
    if (!payload.title) nextFieldErrors.title = 'Tiêu đề không được để trống.';
    if (!payload.content) nextFieldErrors.content = 'Nội dung không được để trống.';
    if (!isValidImageUrl(payload.imageUrl)) nextFieldErrors.imageUrl = 'URL hình ảnh phải bắt đầu bằng http:// hoặc https://.';

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      setSubmitError('Vui lòng kiểm tra lại các trường bắt buộc.');
      return;
    }

    submitLockRef.current = true;
    setSubmitting(true);
    setSubmitError('');
    setFieldErrors({});

    try {
      const response = isEdit
        ? await postsApi.update(id, payload)
        : await postsApi.create(payload);
      clearDraft(draftKey);
      navigate(`/posts/${response.data?.id || id}`);
    } catch (requestError) {
      if (getApiStatus(requestError) === 401) {
        writeDraft(draftKey, form);
        clearAuth();
        navigate('/login', {
          replace: true,
          state: { from: location, draftKey },
        });
        return;
      }

      setFieldErrors(getValidationErrors(requestError));
      setSubmitError(getApiMessage(requestError, 'Không thể lưu bài viết. Vui lòng thử lại.'));
    } finally {
      submitLockRef.current = false;
      setSubmitting(false);
    }
  };

  if (loadingPost) {
    return (
      <div role="status" aria-live="polite" className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
        <div className="mx-auto size-9 animate-spin rounded-full border-4 border-zinc-200 border-t-red-700" aria-hidden="true" />
        <p className="mt-4 text-sm font-bold text-zinc-600">Đang tải bài viết...</p>
      </div>
    );
  }

  if (isEdit && loadError) {
    return (
      <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6" aria-labelledby="edit-load-error">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-red-700">Không tải được bài viết</p>
        <h1 id="edit-load-error" className="font-editorial mt-3 text-3xl font-black text-zinc-950">Chưa thể mở trình chỉnh sửa</h1>
        <p role="alert" className="mt-3 text-sm leading-6 text-red-800">{loadError}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={() => setPostVersion((version) => version + 1)} className="min-h-11 cursor-pointer rounded-lg bg-red-700 px-5 text-sm font-black text-white hover:bg-red-800">Thử tải lại</button>
          <Link to="/admin/posts" className="inline-flex min-h-11 items-center rounded-lg border border-zinc-300 px-5 text-sm font-black text-zinc-900 hover:border-zinc-950">Về trang quản trị</Link>
        </div>
      </section>
    );
  }

  const hasUnknownCurrentCategory = form.categoryId && !categories.some((category) => category.id === form.categoryId);

  return (
    <div className="bg-zinc-50/70 pb-16">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <Link to="/admin/posts" className="inline-flex min-h-11 items-center text-sm font-bold text-zinc-600 transition-colors hover:text-red-700">← Về trang quản trị</Link>
          <p className="mt-4 text-xs font-black uppercase tracking-[0.18em] text-red-700">{isEdit ? 'Chỉnh sửa nội dung' : 'Xuất bản nội dung'}</p>
          <h1 className="font-editorial mt-2 text-4xl font-black tracking-tight text-zinc-950 sm:text-5xl">{isEdit ? 'Sửa bài viết' : 'Tạo bài viết mới'}</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-600">Điền nội dung rõ ràng, chọn chuyên mục phù hợp và kiểm tra lại trước khi lưu.</p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-7 sm:px-6 lg:px-8">
        {draftRestored ? (
          <div role="status" className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            <p><strong>Đã khôi phục bản nháp.</strong> Dữ liệu được giữ lại từ lần phiên đăng nhập gián đoạn.</p>
            <button type="button" onClick={discardDraft} className="min-h-11 cursor-pointer px-3 font-black underline underline-offset-4">Bỏ bản nháp</button>
          </div>
        ) : null}

        {categoryError ? (
          <div role="status" aria-label="Cảnh báo chuyên mục" className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            <p>{categoryError} Bạn vẫn có thể lưu bài không thuộc chuyên mục.</p>
            <button type="button" onClick={() => setCategoryVersion((version) => version + 1)} className="min-h-11 cursor-pointer px-3 font-black underline underline-offset-4">Tải lại chuyên mục</button>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} noValidate className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <section className="space-y-5 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7" aria-labelledby="post-content-heading">
            <h2 id="post-content-heading" className="font-editorial text-2xl font-bold text-zinc-950">Nội dung bài viết</h2>

            {submitError ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">{submitError}</p> : null}

            <div>
              <div className="flex items-center gap-1"><label htmlFor="post-title" className="text-sm font-black text-zinc-900">Tiêu đề</label><span className="text-red-700" aria-hidden="true">*</span></div>
              <input id="post-title" type="text" value={form.title} onChange={updateField('title')} aria-invalid={Boolean(fieldErrors.title)} aria-describedby={fieldErrors.title ? 'post-title-error' : undefined} className="mt-2 min-h-12 w-full rounded-lg border border-zinc-300 px-4 text-base text-zinc-950 outline-none transition focus:border-red-700 focus:ring-4 focus:ring-red-100" placeholder="Nhập tiêu đề bài viết" />
              {fieldErrors.title ? <p id="post-title-error" className="mt-2 text-sm font-semibold text-red-700">{fieldErrors.title}</p> : null}
            </div>

            <div>
              <div className="flex items-center gap-1"><label htmlFor="post-content" className="text-sm font-black text-zinc-900">Nội dung</label><span className="text-red-700" aria-hidden="true">*</span></div>
              <textarea id="post-content" value={form.content} onChange={updateField('content')} aria-invalid={Boolean(fieldErrors.content)} aria-describedby={fieldErrors.content ? 'post-content-error' : undefined} className="mt-2 min-h-80 w-full resize-y rounded-lg border border-zinc-300 px-4 py-3 text-base leading-7 text-zinc-950 outline-none transition focus:border-red-700 focus:ring-4 focus:ring-red-100" placeholder="Nhập nội dung bài viết..." />
              {fieldErrors.content ? <p id="post-content-error" className="mt-2 text-sm font-semibold text-red-700">{fieldErrors.content}</p> : null}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
              <h2 className="font-editorial text-xl font-bold text-zinc-950">Thiết lập xuất bản</h2>
              <div className="mt-5">
                <label htmlFor="post-category" className="text-sm font-black text-zinc-900">Chuyên mục</label>
                <select id="post-category" value={form.categoryId} onChange={updateField('categoryId')} className="mt-2 min-h-12 w-full rounded-lg border border-zinc-300 bg-white px-3 text-sm text-zinc-950 outline-none focus:border-red-700 focus:ring-4 focus:ring-red-100">
                  <option value="">Không chọn chuyên mục</option>
                  {hasUnknownCurrentCategory ? <option value={form.categoryId}>Chuyên mục hiện tại</option> : null}
                  {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
                </select>
              </div>

              <div className="mt-5">
                <label htmlFor="post-image" className="text-sm font-black text-zinc-900">URL hình ảnh</label>
                <input id="post-image" type="url" value={form.imageUrl} onChange={updateField('imageUrl')} aria-invalid={Boolean(fieldErrors.imageUrl)} aria-describedby={fieldErrors.imageUrl ? 'post-image-error' : 'post-image-help'} className="mt-2 min-h-12 w-full rounded-lg border border-zinc-300 px-3 text-sm text-zinc-950 outline-none focus:border-red-700 focus:ring-4 focus:ring-red-100" placeholder="https://..." />
                {fieldErrors.imageUrl ? <p id="post-image-error" className="mt-2 text-sm font-semibold text-red-700">{fieldErrors.imageUrl}</p> : null}
                <p id="post-image-help" className="mt-2 text-xs leading-5 text-zinc-500">SCRUM-29 sử dụng URL ngoài; tải tệp ảnh thuộc SCRUM-39.</p>
              </div>
            </section>

            <button type="submit" disabled={submitting} className="min-h-12 w-full cursor-pointer rounded-lg bg-red-700 px-5 text-sm font-black text-white transition-colors hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-60">
              {submitting ? 'Đang lưu...' : (isEdit ? 'Cập nhật bài viết' : 'Đăng bài')}
            </button>
          </aside>
        </form>
      </main>
    </div>
  );
}
