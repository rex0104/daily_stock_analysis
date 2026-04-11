import React, { useState } from 'react';
import { Button } from '../common';
import { shareApi } from '../../api/share';

interface ShareButtonProps {
  analysisHistoryId: number;
}

/**
 * 分享按钮 — 生成分享链接并复制到剪贴板
 */
export const ShareButton: React.FC<ShareButtonProps> = ({ analysisHistoryId }) => {
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleShare = async () => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const result = await shareApi.create(analysisHistoryId);
      const url = `${window.location.origin}/share/${result.shareToken}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // silently ignore clipboard/network errors
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      variant="home-action-report"
      size="sm"
      isLoading={isLoading}
      loadingText="生成中..."
      onClick={() => void handleShare()}
    >
      {copied ? (
        <>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          已复制分享链接
        </>
      ) : (
        <>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
          分享
        </>
      )}
    </Button>
  );
};
