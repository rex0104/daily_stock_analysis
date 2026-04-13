import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createApiError, createParsedApiError } from '../../api/error';
import { AuthProvider, useAuth } from '../AuthContext';

const { getStatus, register, login, changePassword, logout, resetDashboardState } = vi.hoisted(() => ({
  getStatus: vi.fn(),
  register: vi.fn(),
  login: vi.fn(),
  changePassword: vi.fn(),
  logout: vi.fn(),
  resetDashboardState: vi.fn(),
}));

vi.mock('../../api/auth', () => ({
  authApi: {
    getStatus,
    register,
    login,
    changePassword,
    logout,
  },
}));

vi.mock('../../stores', () => ({
  useStockPoolStore: {
    getState: () => ({
      resetDashboardState,
    }),
  },
}));

const Probe = () => {
  const auth = useAuth();

  return (
    <div>
      <span data-testid="status">{auth.loggedIn ? 'logged-in' : 'logged-out'}</span>
      <span data-testid="has-users">{auth.hasUsers ? 'yes' : 'no'}</span>
      <span data-testid="user-email">{auth.user?.email ?? 'none'}</span>
      <button type="button" onClick={() => void auth.login('test@example.com', 'passwd6')}>
        trigger-login
      </button>
      <button type="button" onClick={() => void auth.logout()}>
        trigger-logout
      </button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('refreshes auth state after a successful login', async () => {
    getStatus
      .mockResolvedValueOnce({
        hasUsers: true,
        loggedIn: false,
        user: null,
      })
      .mockResolvedValueOnce({
        hasUsers: true,
        loggedIn: true,
        user: { id: '1', email: 'test@example.com', nickname: 'Test' },
      });
    login.mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await screen.findByTestId('status');
    fireEvent.click(screen.getByRole('button', { name: 'trigger-login' }));

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('logged-in'));
    expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
  });

  it('refreshes auth state after logout', async () => {
    getStatus
      .mockResolvedValueOnce({
        hasUsers: true,
        loggedIn: true,
        user: { id: '1', email: 'test@example.com', nickname: 'Test' },
      })
      .mockResolvedValueOnce({
        hasUsers: true,
        loggedIn: false,
        user: null,
      });
    logout.mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await screen.findByTestId('status');
    fireEvent.click(screen.getByRole('button', { name: 'trigger-logout' }));

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('logged-out'));
    expect(resetDashboardState).toHaveBeenCalled();
  });

  it('resets dashboard state when not logged in', async () => {
    getStatus.mockResolvedValueOnce({
      hasUsers: false,
      loggedIn: false,
      user: null,
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await screen.findByTestId('status');
    expect(resetDashboardState).toHaveBeenCalled();
  });

  it('treats a 401 logout as already signed out after status refresh', async () => {
    getStatus
      .mockResolvedValueOnce({
        hasUsers: true,
        loggedIn: true,
        user: { id: '1', email: 'test@example.com', nickname: 'Test' },
      })
      .mockResolvedValueOnce({
        hasUsers: true,
        loggedIn: false,
        user: null,
      });
    logout.mockRejectedValue(
      createApiError(
        createParsedApiError({
          title: '未登录',
          message: 'Login required',
          rawMessage: 'Login required',
          status: 401,
          category: 'http_error',
        }),
        { response: { status: 401, data: { error: 'unauthorized' } } }
      )
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await screen.findByTestId('status');
    fireEvent.click(screen.getByRole('button', { name: 'trigger-logout' }));

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('logged-out'));
    expect(resetDashboardState).toHaveBeenCalled();
  });
});
