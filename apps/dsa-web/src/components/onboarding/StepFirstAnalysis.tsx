import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Play, Check, Loader2, AlertCircle, ArrowRight } from 'lucide-react';
import { Button } from '../common';
import { analysisApi } from '../../api/analysis';
import { watchlistApi } from '../../api/watchlist';
import type { WatchlistItem } from '../../api/watchlist';
import { cn } from '../../utils/cn';

type AnalysisStatus = 'idle' | 'analyzing' | 'done' | 'error';

type StockAnalysisResult = {
  stockCode: string;
  stockName: string;
  status: AnalysisStatus;
  score?: number;
  advice?: string;
  error?: string;
};

interface StepFirstAnalysisProps {
  onComplete: () => void;
  addedStocks: { stockCode: string; stockName: string }[];
}

export function StepFirstAnalysis({ onComplete, addedStocks }: StepFirstAnalysisProps) {
  // Derive initial stocks from props synchronously
  const initialStocks = useMemo<StockAnalysisResult[]>(
    () =>
      addedStocks.map((s) => ({
        stockCode: s.stockCode,
        stockName: s.stockName,
        status: 'idle' as AnalysisStatus,
      })),
    [addedStocks]
  );

  const [fallbackStocks, setFallbackStocks] = useState<StockAnalysisResult[]>([]);
  const [analysisResults, setAnalysisResults] = useState<
    Map<string, Omit<StockAnalysisResult, 'stockCode' | 'stockName'>>
  >(new Map());
  const [started, setStarted] = useState(false);
  const [anyDone, setAnyDone] = useState(false);

  // Only fetch watchlist as a fallback when no addedStocks
  useEffect(() => {
    if (addedStocks.length > 0) return;

    let cancelled = false;
    const fetchWatchlist = async () => {
      try {
        const items: WatchlistItem[] = await watchlistApi.list();
        if (!cancelled && items.length > 0) {
          setFallbackStocks(
            items.slice(0, 5).map((item) => ({
              stockCode: item.stockCode,
              stockName: item.stockName || item.stockCode,
              status: 'idle' as AnalysisStatus,
            }))
          );
        }
      } catch {
        // ignore
      }
    };
    void fetchWatchlist();
    return () => { cancelled = true; };
  }, [addedStocks.length]);

  // Merge base stocks with analysis results
  const baseStocks = initialStocks.length > 0 ? initialStocks : fallbackStocks;
  const stocks: StockAnalysisResult[] = useMemo(
    () =>
      baseStocks.map((s) => {
        const result = analysisResults.get(s.stockCode);
        return result ? { ...s, ...result } : s;
      }),
    [baseStocks, analysisResults]
  );

  const analyzeStock = useCallback(
    async (stockCode: string) => {
      setAnalysisResults((prev) => {
        const next = new Map(prev);
        next.set(stockCode, { status: 'analyzing' as AnalysisStatus });
        return next;
      });

      try {
        const result = await analysisApi.analyze({
          stockCode,
          reportType: 'brief',
          forceRefresh: false,
          asyncMode: false,
        });

        // Extract score and advice from sync result
        let score: number | undefined;
        let advice: string | undefined;
        if ('report' in result && result.report?.summary) {
          score = result.report.summary.sentimentScore;
          advice = result.report.summary.operationAdvice;
        }

        setAnalysisResults((prev) => {
          const next = new Map(prev);
          next.set(stockCode, { status: 'done' as AnalysisStatus, score, advice });
          return next;
        });
        setAnyDone(true);
      } catch {
        setAnalysisResults((prev) => {
          const next = new Map(prev);
          next.set(stockCode, { status: 'error' as AnalysisStatus, error: '分析失败' });
          return next;
        });
        // Even on error, allow completing
        setAnyDone(true);
      }
    },
    []
  );

  const handleStart = useCallback(() => {
    if (stocks.length === 0) return;
    setStarted(true);
    // Only analyze the first stock for a fast first result
    void analyzeStock(stocks[0].stockCode);
  }, [stocks, analyzeStock]);

  const getScoreColor = (score?: number) => {
    if (score === undefined) return '';
    if (score <= 20) return 'text-red-400';
    if (score <= 40) return 'text-orange-400';
    if (score <= 60) return 'text-yellow-400';
    if (score <= 80) return 'text-emerald-400';
    return 'text-emerald-300';
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-[var(--login-text-primary)]">
          运行首次分析
        </h3>
        <p className="mt-1 text-sm text-[var(--login-text-secondary)]">
          体验 AI 驱动的股票分析，看看第一份报告
        </p>
      </div>

      {stocks.length === 0 ? (
        <div className="rounded-2xl border border-[var(--login-border-card)] bg-[var(--login-bg-card)]/40 p-6 text-center">
          <p className="text-sm text-[var(--login-text-muted)]">
            暂无关注股票，请返回上一步添加
          </p>
        </div>
      ) : (
        <>
          {/* Stock list */}
          <div className="rounded-2xl border border-[var(--login-border-card)] bg-[var(--login-bg-card)]/40 p-4">
            <p className="mb-3 text-sm text-[var(--login-text-secondary)]">
              准备分析以下股票:
            </p>
            <div className="flex flex-wrap gap-2">
              {stocks.map((stock) => (
                <span
                  key={stock.stockCode}
                  className="inline-flex items-center gap-1 rounded-lg border border-[var(--login-border-card)] px-2.5 py-1 text-sm text-[var(--login-text-primary)]"
                >
                  {stock.stockName}
                </span>
              ))}
            </div>
          </div>

          {/* Start button */}
          {!started && (
            <div className="flex justify-center">
              <Button
                variant="primary"
                size="lg"
                onClick={handleStart}
                className="group/btn relative overflow-hidden bg-gradient-to-r from-[var(--login-brand-button-start)] to-[var(--login-brand-button-end)] text-[var(--login-button-text)] shadow-lg shadow-[0_18px_36px_hsl(214_100%_8%_/_0.24)]"
              >
                <Play className="h-4 w-4" />
                开始分析
                <div className="absolute inset-0 z-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover/btn:animate-[shimmer_1.5s_infinite] pointer-events-none" />
              </Button>
            </div>
          )}

          {/* Analysis progress */}
          <AnimatePresence>
            {started && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-3"
              >
                {stocks.map((stock) => (
                  <motion.div
                    key={stock.stockCode}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                      'flex items-center justify-between rounded-xl border px-4 py-3 transition-colors',
                      stock.status === 'done'
                        ? 'border-emerald-500/20 bg-emerald-500/5'
                        : stock.status === 'error'
                          ? 'border-red-500/20 bg-red-500/5'
                          : 'border-[var(--login-border-card)] bg-[var(--login-bg-card)]/40'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      {stock.status === 'done' ? (
                        <Check className="h-4 w-4 text-emerald-400" />
                      ) : stock.status === 'analyzing' ? (
                        <Loader2 className="h-4 w-4 animate-spin text-[var(--login-accent-text)]" />
                      ) : stock.status === 'error' ? (
                        <AlertCircle className="h-4 w-4 text-red-400" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border border-[var(--login-border-card)]" />
                      )}
                      <span className="text-sm font-medium text-[var(--login-text-primary)]">
                        {stock.stockName}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                      {stock.status === 'done' && stock.score !== undefined && (
                        <>
                          <span className={cn('font-bold', getScoreColor(stock.score))}>
                            {stock.score}分
                          </span>
                          {stock.advice && (
                            <span className="text-[var(--login-text-muted)]">
                              {stock.advice}
                            </span>
                          )}
                        </>
                      )}
                      {stock.status === 'analyzing' && (
                        <span className="text-[var(--login-text-muted)]">分析中...</span>
                      )}
                      {stock.status === 'error' && (
                        <span className="text-red-400">{stock.error}</span>
                      )}
                      {stock.status === 'idle' && started && (
                        <span className="text-[var(--login-text-muted)]">等待中</span>
                      )}
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Complete button */}
          <AnimatePresence>
            {anyDone && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-center pt-2"
              >
                <Button
                  variant="primary"
                  size="lg"
                  onClick={onComplete}
                  className="bg-gradient-to-r from-[var(--login-brand-button-start)] to-[var(--login-brand-button-end)] text-[var(--login-button-text)]"
                >
                  完成设置
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
