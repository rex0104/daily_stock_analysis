import type React from 'react';
import { useState } from 'react';
import type { ParsedApiError } from '../../api/error';
import { isParsedApiError } from '../../api/error';
import { useAuth } from '../../hooks';
import { Button, Input } from '../common';
import { SettingsAlert } from './SettingsAlert';
import { SettingsSectionCard } from './SettingsSectionCard';

export const ChangeNicknameCard: React.FC = () => {
  const { user, updateNickname } = useAuth();
  const [nickname, setNickname] = useState(user?.nickname ?? '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | ParsedApiError | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    const trimmed = nickname.trim();
    if (!trimmed) {
      setError('昵称不能为空');
      return;
    }
    if (trimmed.length > 50) {
      setError('昵称最多 50 个字符');
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await updateNickname(trimmed);
      if (result.success) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 4000);
      } else {
        setError(result.error ?? '修改失败');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SettingsSectionCard
      title="修改昵称"
      description="设置在界面上显示的昵称，默认为注册邮箱前缀。"
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="md:max-w-sm">
          <Input
            id="change-nickname"
            type="text"
            label="昵称"
            placeholder="输入新昵称"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            disabled={isSubmitting}
            autoComplete="nickname"
            maxLength={50}
          />
        </div>

        {error
          ? isParsedApiError(error)
            ? <SettingsAlert title="修改失败" message={error.message} variant="error" className="!mt-3" />
            : <SettingsAlert title="修改失败" message={error} variant="error" className="!mt-3" />
          : null}
        {success ? (
          <SettingsAlert title="修改成功" message="昵称已更新。" variant="success" />
        ) : null}

        <Button type="submit" variant="primary" isLoading={isSubmitting}>
          保存昵称
        </Button>
      </form>
    </SettingsSectionCard>
  );
};
