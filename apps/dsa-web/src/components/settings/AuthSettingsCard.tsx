import type React from 'react';
import { SettingsSectionCard } from './SettingsSectionCard';

/**
 * AuthSettingsCard was the single-admin auth enable/disable toggle.
 * In the multi-user auth model, auth is always enabled and this card
 * is no longer rendered. The export is kept to avoid breaking barrel
 * imports; it renders nothing.
 */
export const AuthSettingsCard: React.FC = () => {
  return (
    <SettingsSectionCard
      title="认证与登录保护"
      description="多用户认证已启用，用户通过注册页面创建账号。"
    >
      <p className="text-sm text-muted-text">
        当前系统使用多用户邮箱密码认证，无需手动开关。
      </p>
    </SettingsSectionCard>
  );
};
