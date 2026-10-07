import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/AuthContext';
import { categoriesApi } from '../services/api';
import Navbar from './Navbar';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('../services/api', () => ({ categoriesApi: { getAll: vi.fn() } }));

describe('Navbar', () => {
  beforeEach(() => {
    categoriesApi.getAll.mockResolvedValue({ data: [] });
  });

  it('chỉ hiện link quản trị cho admin', () => {
    useAuth.mockReturnValue({ status: 'authenticated', user: { role: 'admin' } });
    const { unmount } = render(<MemoryRouter><Navbar /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Quản trị bài viết' })).toHaveAttribute('href', '/admin/posts');
    unmount();

    useAuth.mockReturnValue({ status: 'authenticated', user: { role: 'user' } });
    render(<MemoryRouter><Navbar /></MemoryRouter>);
    expect(screen.queryByRole('link', { name: 'Quản trị bài viết' })).not.toBeInTheDocument();
  });
});
