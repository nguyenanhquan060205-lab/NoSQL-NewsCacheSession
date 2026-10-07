import { StrictMode } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { authApi } from '../services/api';
import { AuthProvider, useAuth } from './AuthContext';

vi.mock('../services/api', () => ({
  authApi: { getMe: vi.fn() },
}));

function AuthProbe() {
  const { user, status, error, refresh, clearAuth } = useAuth();

  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="username">{user?.username || ''}</span>
      <span data-testid="error">{error || ''}</span>
      <button type="button" onClick={refresh}>Thử lại</button>
      <button type="button" onClick={clearAuth}>Xóa auth</button>
    </div>
  );
}

describe('AuthProvider', () => {
  beforeEach(() => {
    authApi.getMe.mockReset();
  });

  it('gom request getMe đang chạy khi StrictMode mount lại component', async () => {
    let resolveRequest;
    authApi.getMe.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve; }));

    render(
      <StrictMode>
        <AuthProvider><AuthProbe /></AuthProvider>
      </StrictMode>,
    );

    expect(screen.getByTestId('status')).toHaveTextContent('loading');
    expect(authApi.getMe).toHaveBeenCalledTimes(1);

    resolveRequest({ data: { username: 'admin1', role: 'admin' } });

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'));
    expect(screen.getByTestId('username')).toHaveTextContent('admin1');
  });

  it('phân biệt 401 với lỗi mạng và cho phép thử lại', async () => {
    const user = userEvent.setup();
    authApi.getMe
      .mockRejectedValueOnce({ response: { status: 500 } })
      .mockResolvedValueOnce({ data: { username: 'admin1', role: 'admin' } });

    render(<AuthProvider><AuthProbe /></AuthProvider>);

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('error'));
    expect(screen.getByTestId('error')).not.toHaveTextContent('');

    await user.click(screen.getByRole('button', { name: 'Thử lại' }));
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'));
  });

  it('đánh dấu unauthenticated khi API trả 401', async () => {
    authApi.getMe.mockRejectedValue({ response: { status: 401 } });

    render(<AuthProvider><AuthProbe /></AuthProvider>);

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'));
    expect(screen.getByTestId('error')).toHaveTextContent('');
  });

  it('không tái dùng request getMe cũ sau khi clear auth', async () => {
    const user = userEvent.setup();
    let resolveOldRequest;
    authApi.getMe
      .mockReturnValueOnce(new Promise((resolve) => { resolveOldRequest = resolve; }))
      .mockResolvedValueOnce({ data: { username: 'admin-moi', role: 'admin' } });

    render(<AuthProvider><AuthProbe /></AuthProvider>);

    await user.click(screen.getByRole('button', { name: 'Xóa auth' }));
    await user.click(screen.getByRole('button', { name: 'Thử lại' }));

    await waitFor(() => expect(authApi.getMe).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('admin-moi'));

    resolveOldRequest({ data: { username: 'admin-cu', role: 'admin' } });
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('admin-moi'));
  });
});
