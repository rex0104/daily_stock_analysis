import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { Card } from '../common';
import { DashboardPanelHeader, DashboardStateBlock } from '../dashboard';
import { watchlistApi, type WatchlistItem } from '../../api/watchlist';

interface WatchlistPanelProps {
  onAnalyze: (stockCode: string) => void;
  /** Controlled items list; when provided, the panel syncs from this instead of fetching independently */
  items?: WatchlistItem[];
  /** Called when the items list changes (add / remove) */
  onItemsChange?: (items: WatchlistItem[]) => void;
}

export const WatchlistPanel: React.FC<WatchlistPanelProps> = ({
  onAnalyze,
  items: controlledItems,
  onItemsChange,
}) => {
  const isControlled = controlledItems !== undefined;
  const [internalItems, setInternalItems] = useState<WatchlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(!isControlled);
  const [removingCodes, setRemovingCodes] = useState<Set<string>>(new Set());

  const items = isControlled ? controlledItems : internalItems;

  const updateItems = useCallback(
    (updater: (prev: WatchlistItem[]) => WatchlistItem[]) => {
      if (isControlled) {
        const next = updater(controlledItems ?? []);
        onItemsChange?.(next);
      } else {
        setInternalItems((prev) => {
          const next = updater(prev);
          onItemsChange?.(next);
          return next;
        });
      }
    },
    [isControlled, controlledItems, onItemsChange],
  );

  useEffect(() => {
    if (isControlled) return;
    let cancelled = false;
    setIsLoading(true);
    watchlistApi
      .list()
      .then((data) => {
        if (!cancelled) {
          setInternalItems(data);
          onItemsChange?.(data);
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isControlled, onItemsChange]);

  const handleRemove = useCallback(
    async (stockCode: string) => {
      setRemovingCodes((prev) => new Set(prev).add(stockCode));
      try {
        await watchlistApi.remove(stockCode);
        updateItems((prev) => prev.filter((item) => item.stockCode !== stockCode));
      } catch {
        // silently fail
      } finally {
        setRemovingCodes((prev) => {
          const next = new Set(prev);
          next.delete(stockCode);
          return next;
        });
      }
    },
    [updateItems],
  );

  return (
    <Card
      variant="bordered"
      padding="none"
      className="home-panel-card overflow-hidden shrink-0"
    >
      <div className="border-b border-subtle px-3 py-3">
        <DashboardPanelHeader
          className="mb-0"
          title="我的自选"
          titleClassName="text-sm font-medium"
          leading={(
            <svg className="h-4 w-4 text-amber-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          )}
          headingClassName="items-center"
        />
      </div>

      <div className="max-h-48 overflow-y-auto p-2">
        {isLoading ? (
          <DashboardStateBlock loading compact title="加载中..." />
        ) : items.length === 0 ? (
          <p className="px-2 py-3 text-center text-xs text-muted-text">
            还没有自选股，分析后点击 ⭐ 收藏
          </p>
        ) : (
          <div className="space-y-1.5">
            {items.map((item) => {
              const isRemoving = removingCodes.has(item.stockCode);
              return (
                <div
                  key={item.stockCode}
                  className="home-subpanel flex items-center gap-2 px-2.5 py-2"
                >
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-semibold text-foreground truncate block leading-tight">
                      {item.stockName || item.stockCode}
                    </span>
                    <span className="text-[11px] text-secondary-text font-mono">
                      {item.stockCode}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => onAnalyze(item.stockCode)}
                    className="flex-shrink-0 rounded-lg border border-subtle bg-surface/60 px-2 py-1 text-[11px] text-secondary-text transition-colors hover:border-subtle-hover hover:text-foreground"
                  >
                    分析
                  </button>

                  <button
                    type="button"
                    onClick={() => void handleRemove(item.stockCode)}
                    disabled={isRemoving}
                    aria-label={`移除 ${item.stockName || item.stockCode}`}
                    className="flex-shrink-0 rounded-lg p-1 text-muted-text transition-colors hover:text-danger disabled:opacity-40"
                  >
                    {isRemoving ? (
                      <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    ) : (
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
};

export default WatchlistPanel;
