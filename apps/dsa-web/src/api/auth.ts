import apiClient from './index';

export type AuthUser = {
  id: string;
  email: string;
  nickname: string;
};

export type AuthStatusResponse = {
  hasUsers: boolean;
  loggedIn: boolean;
  user: AuthUser | null;
  onboardingCompleted: boolean;
};

export const authApi = {
  async getStatus(): Promise<AuthStatusResponse> {
    const { data } = await apiClient.get<AuthStatusResponse>('/api/v1/auth/status');
    return data;
  },

  async register(
    email: string,
    password: string,
    passwordConfirm: string
  ): Promise<void> {
    await apiClient.post('/api/v1/auth/register', {
      email,
      password,
      passwordConfirm,
    });
  },

  async login(email: string, password: string): Promise<void> {
    await apiClient.post('/api/v1/auth/login', { email, password });
  },

  async changePassword(
    currentPassword: string,
    newPassword: string,
    newPasswordConfirm: string
  ): Promise<void> {
    await apiClient.post('/api/v1/auth/change-password', {
      currentPassword,
      newPassword,
      newPasswordConfirm,
    });
  },

  async forgotPassword(email: string): Promise<void> {
    await apiClient.post('/api/v1/auth/forgot-password', { email });
  },

  async resetPassword(
    token: string,
    password: string,
    passwordConfirm: string
  ): Promise<void> {
    await apiClient.post('/api/v1/auth/reset-password', {
      token,
      password,
      passwordConfirm,
    });
  },

  async updateNickname(nickname: string): Promise<AuthUser> {
    const { data } = await apiClient.put<AuthUser>('/api/v1/auth/nickname', { nickname });
    return data;
  },

  async logout(): Promise<void> {
    await apiClient.post('/api/v1/auth/logout');
  },
};
