import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Star } from 'lucide-react';
import { PageHeader, EmptyState } from '../components/common';
import { AppPage } from '../components/common/AppPage';
import { watchlistApi, type WatchlistItem } from '../api/watchlist';

const WatchlistPage: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [removingCodes, setRemovingCodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    document.title = '我的自选 - DSA';
    watchlistApi
      .list()
      .then(setItems)
      .catch(() => undefined)
      .finally(() => setIsLoading(false));
  }, []);

  const handleAnalyze = useCallback(
    (stockCode: string) => {
      navigate(`/?q=${encodeURIComponent(stockCode)}`);
    },
    [navigate],
  );

  const handleRemove = useCallback(async (stockCode: string) => {
    setRemovingCodes((prev) => new Set(prev).add(stockCode));
    try {
      await watchlistApi.remove(stockCode);
      setItems((prev) => prev.filter((item) => item.stockCode !== stockCode));
    } catch {
      // silently fail
    } finally {
      setRemovingCodes((prev) => {
        const next = new Set(prev);
        next.delete(stockCode);
        return next;
      });
    }
  }, []);

  return (
    <AppPage>
      <PageHeader
        eyebrow="Watchlist"
        title="我的自选"
        description="收藏感兴趣的股票，快速发起分析"
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Star className="h-10 w-10 text-muted-text" />}
          title="还没有自选股"
          description="在首页搜索股票并点击 ⭐ 收藏，自选股会显示在这里"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => {
            const isRemoving = removingCodes.has(item.stockCode);
            return (
              <div
                key={item.stockCode}
                className="home-panel-card flex items-center gap-3 px-4 py-4 transition-all hover:shadow-soft-card-strong"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">
                    {item.stockName || item.stockCode}
                  </p>
                  <p className="text-xs text-secondary-text font-mono mt-0.5">
                    {item.stockCode}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => handleAnalyze(item.stockCode)}
                  className="shrink-0 rounded-lg border border-subtle bg-surface/60 px-3 py-1.5 text-xs text-secondary-text transition-colors hover:border-subtle-hover hover:text-foreground"
                >
                  分析
                </button>

                <button
                  type="button"
                  onClick={() => void handleRemove(item.stockCode)}
                  disabled={isRemoving}
                  aria-label={`移除 ${item.stockName || item.stockCode}`}
                  className="shrink-0 rounded-lg p-1.5 text-muted-text transition-colors hover:text-danger disabled:opacity-40"
                >
                  {isRemoving ? (
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  ) : (
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </AppPage>
  );
};

export default WatchlistPage;
