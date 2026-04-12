import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Plus, TrendingUp } from 'lucide-react';
import { StockAutocomplete } from '../StockAutocomplete';
import { watchlistApi } from '../../api/watchlist';
import { cn } from '../../utils/cn';

type AddedStock = {
  stockCode: string;
  stockName: string;
};

const POPULAR_STOCKS: AddedStock[] = [
  { stockCode: '600519', stockName: '贵州茅台' },
  { stockCode: 'AAPL', stockName: 'Apple' },
  { stockCode: 'hk00700', stockName: '腾讯控股' },
  { stockCode: '002594', stockName: '比亚迪' },
  { stockCode: 'TSLA', stockName: 'Tesla' },
  { stockCode: '300750', stockName: '宁德时代' },
];

interface StepAddStocksProps {
  onComplete: () => void;
  addedStocks: AddedStock[];
  setAddedStocks: React.Dispatch<React.SetStateAction<AddedStock[]>>;
}

export function StepAddStocks({ onComplete, addedStocks, setAddedStocks }: StepAddStocksProps) {
  const [searchValue, setSearchValue] = useState('');
  const [adding, setAdding] = useState<string | null>(null);

  const addStock = useCallback(
    async (code: string, name?: string) => {
      if (addedStocks.some((s) => s.stockCode === code)) return;
      setAdding(code);
      try {
        await watchlistApi.add(code, name);
        const newStock = { stockCode: code, stockName: name || code };
        setAddedStocks((prev) => [...prev, newStock]);
        setSearchValue('');
        // Mark step complete as soon as first stock added
        if (addedStocks.length === 0) {
          onComplete();
        }
      } catch {
        // Silently handle — stock may already be in watchlist
        const newStock = { stockCode: code, stockName: name || code };
        if (!addedStocks.some((s) => s.stockCode === code)) {
          setAddedStocks((prev) => [...prev, newStock]);
          if (addedStocks.length === 0) {
            onComplete();
          }
        }
      } finally {
        setAdding(null);
      }
    },
    [addedStocks, onComplete, setAddedStocks]
  );

  const removeStock = useCallback(
    async (code: string) => {
      try {
        await watchlistApi.remove(code);
      } catch {
        // ignore removal failure
      }
      setAddedStocks((prev) => prev.filter((s) => s.stockCode !== code));
    },
    [setAddedStocks]
  );

  const handleAutocompleteSubmit = useCallback(
    (code: string, name?: string) => {
      void addStock(code, name);
    },
    [addStock]
  );

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-[var(--login-text-primary)]">
          添加关注股票
        </h3>
        <p className="mt-1 text-sm text-[var(--login-text-secondary)]">
          搜索或从热门推荐中选择，添加到你的自选列表
        </p>
      </div>

      {/* Search input */}
      <div className="relative">
        <StockAutocomplete
          value={searchValue}
          onChange={setSearchValue}
          onSubmit={handleAutocompleteSubmit}
          placeholder="搜索股票代码或名称..."
          className="!rounded-2xl !border-[var(--login-border-card)] !bg-[var(--login-bg-card)]/40 !text-[var(--login-text-primary)] placeholder:!text-[var(--login-text-muted)]"
        />
      </div>

      {/* Popular suggestions */}
      <div>
        <p className="mb-3 text-sm font-medium text-[var(--login-text-secondary)]">
          热门推荐
        </p>
        <div className="flex flex-wrap gap-2">
          {POPULAR_STOCKS.map((stock) => {
            const isAdded = addedStocks.some((s) => s.stockCode === stock.stockCode);
            const isAdding = adding === stock.stockCode;
            return (
              <button
                key={stock.stockCode}
                type="button"
                disabled={isAdded || isAdding}
                onClick={() => void addStock(stock.stockCode, stock.stockName)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-sm transition-all duration-200',
                  isAdded
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : 'border-[var(--login-border-card)] bg-transparent text-[var(--login-text-secondary)] hover:border-[var(--login-accent-border)] hover:bg-[var(--login-accent-soft)] hover:text-[var(--login-accent-text)]'
                )}
              >
                {isAdding ? (
                  <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : isAdded ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <Plus className="h-3 w-3" />
                )}
                <span>{stock.stockName}</span>
                <span className="text-xs opacity-60">{stock.stockCode}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Added stocks list */}
      <AnimatePresence>
        {addedStocks.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <p className="mb-3 text-sm font-medium text-[var(--login-text-secondary)]">
              已添加 ({addedStocks.length})
            </p>
            <div className="space-y-2">
              {addedStocks.map((stock) => (
                <motion.div
                  key={stock.stockCode}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  className="flex items-center justify-between rounded-xl border border-[var(--login-border-card)] bg-[var(--login-bg-card)]/40 px-4 py-2.5"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-emerald-400" />
                    <span className="text-sm font-medium text-[var(--login-text-primary)]">
                      {stock.stockName}
                    </span>
                    <span className="text-xs text-[var(--login-text-muted)]">
                      {stock.stockCode}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void removeStock(stock.stockCode)}
                    className="rounded-lg p-1 text-[var(--login-text-muted)] transition-colors hover:bg-red-500/10 hover:text-red-400"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
