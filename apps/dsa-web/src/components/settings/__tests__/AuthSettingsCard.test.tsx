import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AuthSettingsCard } from '../AuthSettingsCard';

describe('AuthSettingsCard', () => {
  it('renders a static informational message about multi-user auth', () => {
    render(<AuthSettingsCard />);

    expect(screen.getByText('认证与登录保护')).toBeInTheDocument();
    expect(screen.getByText('当前系统使用多用户邮箱密码认证，无需手动开关。')).toBeInTheDocument();
  });
});
