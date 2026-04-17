import type React from 'react';
import type { ScreenerCandidate } from '../../api/screener';
import { cn } from '../../utils/cn';

interface ScreenerResultItemProps {
  candidate: ScreenerCandidate;
  onAnalyze: (code: string) => void;
  onAddWatchlist: (code: string, name: string) => void;
}

export const ScreenerResultItem: React.FC<ScreenerResultItemProps> = ({
  candidate,
  onAnalyze,
  onAddWatchlist,
}) => {
  const isPositive = candidate.changePct >= 0;
  const colorClass = isPositive ? 'text-[#ef4444]' : 'text-[#22c55e]';

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-subtle bg-surface p-4 sm:flex-row sm:items-center sm:gap-4">
      {/* Stock info */}
      <div className="min-w-[90px]">
        <div className="text-sm font-semibold text-foreground">{candidate.name}</div>
        <div className="text-xs text-muted-text">{candidate.code}</div>
      </div>

      {/* Price */}
      <div className="min-w-[80px] sm:text-right">
        <div className={cn('text-sm font-semibold', colorClass)}>
          {candidate.price.toFixed(2)}
        </div>
        <div className={cn('text-xs', colorClass)}>
          {isPositive ? '+' : ''}{candidate.changePct.toFixed(2)}%
        </div>
      </div>

      {/* Indicators */}
      <div className="flex gap-4 text-center">
        <div>
          <div className="text-[10px] text-muted-text">量比</div>
          <div className="text-xs font-semibold text-amber-500">{candidate.volumeRatio}</div>
        </div>
        <div>
          <div className="text-[10px] text-muted-text">5日涨幅</div>
          <div className={cn('text-xs font-semibold', candidate.pct5d >= 0 ? 'text-[#ef4444]' : 'text-[#22c55e]')}>
            {candidate.pct5d >= 0 ? '+' : ''}{candidate.pct5d}%
          </div>
        </div>
      </div>

      {/* AI Summary */}
      <div className="flex-1 border-l border-subtle pl-3 text-xs leading-relaxed text-secondary-text sm:min-w-0">
        {candidate.summary ? (
          candidate.summary
        ) : (
          <span className="flex items-center gap-1.5 text-muted-text italic">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-[hsl(var(--primary))]/20 border-t-[hsl(var(--primary))]" />
            AI 摘要生成中...
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={() => onAnalyze(candidate.code)}
          className="rounded-lg border border-subtle bg-surface-hover px-3 py-1.5 text-xs text-secondary-text transition-colors hover:text-foreground"
        >
          分析
        </button>
        <button
          type="button"
          onClick={() => onAddWatchlist(candidate.code, candidate.name)}
          className="rounded-lg border border-subtle bg-surface-hover px-3 py-1.5 text-xs text-secondary-text transition-colors hover:text-foreground"
        >
          + 自选
        </button>
      </div>
    </div>
  );
};
