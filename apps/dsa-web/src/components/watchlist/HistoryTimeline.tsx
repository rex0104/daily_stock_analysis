import type React from 'react';
import type { WatchlistTimelineEntry } from '../../api/watchlist';
import { cn } from '../../utils/cn';

interface HistoryTimelineProps {
  entries: WatchlistTimelineEntry[];
}

function sentimentEmoji(score: number): string {
  if (score >= 60) return '\u{1F60A}';
  if (score >= 40) return '\u{1F610}';
  return '\u{1F61F}';
}

function sentimentVariant(score: number): 'bullish' | 'neutral' | 'bearish' {
  if (score >= 60) return 'bullish';
  if (score >= 40) return 'neutral';
  return 'bearish';
}

const variantStyles: Record<string, string> = {
  bullish: 'border-cyan/30 bg-cyan/10 text-cyan',
  neutral: 'border-purple/20 bg-purple/10 text-purple',
  bearish: 'border-danger/20 bg-danger/10 text-danger',
};

/**
 * Horizontal row of analysis history chips showing date, sentiment, and advice.
 */
export const HistoryTimeline: React.FC<HistoryTimelineProps> = ({ entries }) => {
  if (entries.length === 0) {
    return (
      <p className="text-xs text-muted-text">
        暂无分析历史
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map((entry) => {
        const variant = sentimentVariant(entry.sentimentScore);
        const dateShort = entry.date.slice(5); // "MM-DD"
        return (
          <span
            key={entry.date}
            className={cn(
              'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium backdrop-blur-sm',
              variantStyles[variant],
            )}
          >
            {dateShort} {sentimentEmoji(entry.sentimentScore)}{entry.sentimentScore} {entry.operationAdvice}
          </span>
        );
      })}
    </div>
  );
};
