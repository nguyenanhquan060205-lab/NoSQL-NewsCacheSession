import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/useAuth';
import { authApi } from '../services/api';
import AdminSessionsPage from './AdminSessionsPage';

vi.mock('../context/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../services/api', () => ({
  authApi: { getActiveSessions: vi.fn(), revokeSession: vi.fn() },
}));

const currentSession = {
  sessionId: 'current-session', userId: 'user-1', username: 'admin', role: 'admin',
  loginAt: '2026-10-07T08:00:00Z', lastActive: '2026-10-07T08:20:00Z',
  expiresInSeconds: 1200, isCurrent: true,
};
const otherSession = {
  ...currentSession, sessionId: 'session-2', username: 'reader', role: 'user',
  isCurrent: false, expiresInSeconds: 75,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/sessions']}>
      <Routes>
        <Route path="/admin/sessions" element={<AdminSessionsPage />} />
        <Route path="/login" element={<p>Trang đăng nhập</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminSessionsPage', () => {
  beforeEach(() => {
    vi.useRealTimers();
    useAuth.mockReturnValue({ clearAuth: vi.fn() });
    authApi.getActiveSessions.mockResolvedValue({ data: [currentSession, otherSession] });
    authApi.revokeSession.mockResolvedValue({ status: 204 });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  });

  it('loads the session list and shows identity, activity, expiry and current-session protection', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Phiên truy cập.' })).toBeInTheDocument();
    expect(authApi.getActiveSessions).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('article', { name: 'Phiên của admin' })).toBeInTheDocument();
    expect(screen.getByRole('article', { name: 'Phiên của reader' })).toBeInTheDocument();
    expect(screen.getByText('Phiên hiện tại')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Thu hồi phiên của reader' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Thu hồi phiên của admin' })).not.toBeInTheDocument();
  });

  it('retries a failed list request without clearing the authenticated user', async () => {
    const clearAuth = vi.fn();
    const user = userEvent.setup();
    useAuth.mockReturnValue({ clearAuth });
    authApi.getActiveSessions
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce({ data: [currentSession] });
    renderPage();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Thử tải lại' }));
    expect(await screen.findByRole('article', { name: 'Phiên của admin' })).toBeInTheDocument();
    expect(clearAuth).not.toHaveBeenCalled();
  });

  it('redirects to login and clears auth when the list endpoint returns 401', async () => {
    const clearAuth = vi.fn();
    useAuth.mockReturnValue({ clearAuth });
    authApi.getActiveSessions.mockRejectedValue({ response: { status: 401 } });
    renderPage();

    expect(await screen.findByText('Trang đăng nhập')).toBeInTheDocument();
    expect(clearAuth).toHaveBeenCalledTimes(1);
  });

  it('does not keep displaying a previously available session list after access is forbidden', async () => {
    authApi.getActiveSessions
      .mockResolvedValueOnce({ data: [currentSession] })
      .mockRejectedValueOnce({ response: { status: 403, data: { message: 'Chỉ admin được xem.' } } });
    renderPage();
    expect(await screen.findByRole('article', { name: 'Phiên của admin' })).toBeInTheDocument();

    await act(async () => { window.dispatchEvent(new Event('focus')); });

    expect(await screen.findByRole('alert')).toHaveTextContent('Chỉ admin được xem.');
    expect(screen.queryByRole('article', { name: 'Phiên của admin' })).not.toBeInTheDocument();
  });

  it('polls every 30 seconds only while visible and refreshes on visibility return', async () => {
    vi.useFakeTimers();
    renderPage();
    await act(async () => { await Promise.resolve(); });
    expect(authApi.getActiveSessions).toHaveBeenCalledTimes(1);

    await act(async () => { vi.advanceTimersByTime(29_999); });
    expect(authApi.getActiveSessions).toHaveBeenCalledTimes(1);
    await act(async () => { vi.advanceTimersByTime(1); });
    expect(authApi.getActiveSessions).toHaveBeenCalledTimes(2);

    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
    await act(async () => { document.dispatchEvent(new Event('visibilitychange')); });
    await act(async () => { vi.advanceTimersByTime(30_000); });
    expect(authApi.getActiveSessions).toHaveBeenCalledTimes(2);

    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
    await act(async () => { document.dispatchEvent(new Event('visibilitychange')); });
    expect(authApi.getActiveSessions).toHaveBeenCalledTimes(3);
  });

  it('labels a Redis key without expiry instead of showing a false zero-second TTL', async () => {
    authApi.getActiveSessions.mockResolvedValue({
      data: [{ ...currentSession, expiresInSeconds: -1 }],
    });
    renderPage();

    const card = await screen.findByRole('article', { name: 'Phiên của admin' });
    expect(within(card).getByLabelText('Không giới hạn TTL')).toHaveTextContent('Không giới hạn');
  });

  it('confirms and revokes a non-current session, then reloads the list', async () => {
    const user = userEvent.setup();
    renderPage();
    const card = await screen.findByRole('article', { name: 'Phiên của reader' });
    await user.click(within(card).getByRole('button', { name: 'Thu hồi phiên của reader' }));

    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => expect(authApi.revokeSession).toHaveBeenCalledWith('session-2'));
    await waitFor(() => expect(authApi.getActiveSessions).toHaveBeenCalledTimes(2));
  });

  it('does not revoke when confirmation is declined', async () => {
    const user = userEvent.setup();
    window.confirm.mockReturnValue(false);
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Thu hồi phiên của reader' }));
    expect(authApi.revokeSession).not.toHaveBeenCalled();
  });

  it('keeps the row and shows the server error when revoke fails', async () => {
    const user = userEvent.setup();
    authApi.revokeSession.mockRejectedValue({ response: { status: 403, data: { message: 'Không đủ quyền.' } } });
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Thu hồi phiên của reader' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Không đủ quyền.');
    expect(screen.queryByText('reader')).not.toBeInTheDocument();
  });
});
