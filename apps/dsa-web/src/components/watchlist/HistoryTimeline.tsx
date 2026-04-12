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

function sentimentColor(score: number): string {
  if (score >= 60) return 'text-cyan';
  if (score >= 40) return 'text-purple';
  return 'text-danger';
}

function dotColor(score: number): string {
  if (score >= 60) return 'bg-cyan';
  if (score >= 40) return 'bg-purple';
  return 'bg-danger';
}

export const HistoryTimeline: React.FC<HistoryTimelineProps> = ({ entries }) => {
  if (entries.length === 0) {
    return (
      <p className="text-xs text-muted-text py-1">暂无分析历史</p>
    );
  }

  return (
    <div className="space-y-0">
      {entries.map((entry, idx) => {
        const dateShort = entry.date.slice(5); // "MM-DD"
        const isLast = idx === entries.length - 1;
        return (
          <div key={entry.date} className="flex gap-3">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div className={cn('h-2 w-2 rounded-full shrink-0 mt-1.5', dotColor(entry.sentimentScore))} />
              {!isLast && <div className="w-px flex-1 bg-border/50 my-0.5" />}
            </div>
            {/* Content */}
            <div className={cn('pb-3 min-w-0', isLast && 'pb-0')}>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-text font-mono">{dateShort}</span>
                <span className={cn('font-medium', sentimentColor(entry.sentimentScore))}>
                  {sentimentEmoji(entry.sentimentScore)} {entry.sentimentScore}
                </span>
                <span className="text-secondary-text">{entry.operationAdvice}</span>
              </div>
              {entry.analysisSummary && (
                <p className="mt-0.5 text-xs text-secondary-text line-clamp-2 leading-relaxed">
                  {entry.analysisSummary}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
