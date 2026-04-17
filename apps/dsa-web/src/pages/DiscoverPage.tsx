import type React from 'react';
import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/common';
import { StrategyCard } from '../components/screener/StrategyCard';
import { ScreenerResultItem } from '../components/screener/ScreenerResultItem';
import { screenerApi, type Strategy, type ScreenerCandidate } from '../api/screener';
import { watchlistApi } from '../api/watchlist';

type SortKey = 'volume_ratio' | 'change_pct' | 'pct_5d';

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'volume_ratio', label: '按量比排序' },
  { key: 'change_pct', label: '按涨幅排序' },
  { key: 'pct_5d', label: '按5日涨幅排序' },
];

const DiscoverPage: React.FC = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [candidates, setCandidates] = useState<ScreenerCandidate[]>([]);
  const [scanStats, setScanStats] = useState<{ total: number; matched: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('volume_ratio');
  const cleanupRef = useRef<(() => void) | null>(null);

  // Load strategies on mount
  useEffect(() => {
    screenerApi.listStrategies().then(setStrategies).catch(() => {});
    return () => { cleanupRef.current?.(); };
  }, []);

  const handleScan = useCallback(() => {
    if (!selectedStrategy || scanning) return;
    setScanning(true);
    setCandidates([]);
    setScanStats(null);
    setError(null);

    cleanupRef.current?.();
    cleanupRef.current = screenerApi.scan(
      selectedStrategy,
      (type, data) => {
        if (type === 'candidates') {
          const items = (data as unknown as Record<string, unknown>[]).map((c) => ({
            code: c.code as string,
            name: c.name as string,
            price: c.price as number,
            changePct: (c.change_pct as number) ?? 0,
            volumeRatio: (c.volume_ratio as number) ?? 0,
            pct5d: (c.pct_5d as number) ?? 0,
          }));
          setCandidates(items);
        } else if (type === 'summary') {
          const { code, summary } = data as { code: string; summary: string };
          setCandidates((prev) =>
            prev.map((c) => (c.code === code ? { ...c, summary } : c)),
          );
        } else if (type === 'done') {
          setScanStats(data as { total: number; matched: number });
          setScanning(false);
        } else if (type === 'error') {
          setError((data as { message: string }).message);
          setScanning(false);
        }
      },
      () => {
        setError('扫描连接中断');
        setScanning(false);
      },
    );
  }, [selectedStrategy, scanning]);

  const handleAnalyze = useCallback(
    (code: string) => navigate(`/?q=${code}`),
    [navigate],
  );

  const handleAddWatchlist = useCallback(async (code: string, name: string) => {
    try {
      await watchlistApi.add(code, name);
    } catch { /* toast could go here */ }
  }, []);

  // Sort candidates
  const sorted = [...candidates].sort((a, b) => {
    if (sortKey === 'volume_ratio') return b.volumeRatio - a.volumeRatio;
    if (sortKey === 'change_pct') return b.changePct - a.changePct;
    return b.pct5d - a.pct5d;
  });

  const selectedDef = strategies.find((s) => s.id === selectedStrategy);

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-6 sm:px-6">
      <PageHeader title="AI 智能选股" description="选择策略，发现 A 股市场机会" />

      {/* Strategy cards */}
      <div>
        <div className="mb-2.5 text-[10px] uppercase tracking-widest text-muted-text">选择策略</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {strategies.map((s) => (
            <StrategyCard
              key={s.id}
              id={s.id}
              name={s.name}
              description={s.description}
              icon={s.icon}
              selected={selectedStrategy === s.id}
              disabled={scanning}
              onSelect={() => setSelectedStrategy(s.id)}
            />
          ))}
        </div>
      </div>

      {/* Scan button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleScan}
          disabled={!selectedStrategy || scanning}
          className="btn-primary disabled:opacity-50"
        >
          {scanning ? '扫描中...' : '开始扫描'}
        </button>
        {scanning && (
          <span className="text-xs text-muted-text">预计耗时 30-60 秒（含 AI 摘要）</span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
          <button
            type="button"
            onClick={handleScan}
            className="ml-3 underline"
          >
            重试
          </button>
        </div>
      )}

      {/* Results */}
      {candidates.length > 0 && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm text-foreground">
              扫描结果
              {selectedDef && (
                <span className="ml-1.5 font-semibold text-[hsl(var(--primary))]">· {selectedDef.name}</span>
              )}
              {scanStats && (
                <span className="ml-2 text-xs text-muted-text">
                  命中 {scanStats.matched} 只 / {scanStats.total} 只
                </span>
              )}
            </div>
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="rounded-lg border border-subtle bg-surface px-2.5 py-1 text-xs text-secondary-text"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            {sorted.map((c) => (
              <ScreenerResultItem
                key={c.code}
                candidate={c}
                onAnalyze={handleAnalyze}
                onAddWatchlist={handleAddWatchlist}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state after scan completes */}
      {!scanning && scanStats && candidates.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-sm text-muted-text">
          当前策略未匹配到符合条件的股票
        </div>
      )}
    </div>
  );
};

export default DiscoverPage;
