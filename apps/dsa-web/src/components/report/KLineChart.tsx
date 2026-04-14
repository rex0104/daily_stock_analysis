import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import type { IChartApi, Time } from 'lightweight-charts';
import { useTheme } from 'next-themes';
import { stocksApi, type KlineBar } from '../../api/stocks';

// CN stock color convention: up = red, down = green
const UP_COLOR = '#ef4444';
const DOWN_COLOR = '#22c55e';
const MA5_COLOR = '#f59e0b';   // amber
const MA20_COLOR = '#a78bfa';  // purple

type Period = 'daily' | 'weekly';

function calcMA(bars: KlineBar[], period: number): { time: Time; value: number }[] {
  const result: { time: Time; value: number }[] = [];
  for (let i = period - 1; i < bars.length; i++) {
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += bars[j].close;
    result.push({ time: bars[i].date as Time, value: +(sum / period).toFixed(3) });
  }
  return result;
}

interface KLineChartProps {
  stockCode: string;
}

export const KLineChart: React.FC<KLineChartProps> = ({ stockCode }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [bars, setBars] = useState<KlineBar[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<Period>('daily');
  const { resolvedTheme } = useTheme();

  // Fetch K-line data whenever stock or period changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setBars(null);
    const days = period === 'daily' ? 90 : 365;
    stocksApi
      .getKlineHistory(stockCode, days, period)
      .then((data) => { if (!cancelled) setBars(data); })
      .catch(() => { if (!cancelled) setBars([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [stockCode, period]);

  // Create / recreate chart whenever data or theme changes
  useEffect(() => {
    if (!containerRef.current || !bars || bars.length === 0) return;

    const isDark = resolvedTheme !== 'light';
    const textColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.05)';

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      rightPriceScale: { borderVisible: false },
      leftPriceScale: { visible: false, borderVisible: false },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: { mode: CrosshairMode.Normal },
    });
    chartRef.current = chart;

    // ── Candlestick ────────────────────────────────────────────────
    const candleSeries = chart.addCandlestickSeries({
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      borderUpColor: UP_COLOR,
      borderDownColor: DOWN_COLOR,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
    });
    candleSeries.setData(
      bars.map((b) => ({
        time: b.date as Time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );
    // Leave bottom 28% for volume
    chart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.08, bottom: 0.28 },
    });

    // ── Volume ─────────────────────────────────────────────────────
    const hasVolume = bars.some((b) => b.volume != null && b.volume > 0);
    if (hasVolume) {
      const volSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
      });
      volSeries.setData(
        bars.map((b) => ({
          time: b.date as Time,
          value: b.volume ?? 0,
          color: b.close >= b.open ? `${UP_COLOR}88` : `${DOWN_COLOR}88`,
        })),
      );
      chart.priceScale('vol').applyOptions({
        scaleMargins: { top: 0.78, bottom: 0 },
        visible: false,
      });
    }

    // ── MA lines ───────────────────────────────────────────────────
    const ma5Data = calcMA(bars, 5);
    if (ma5Data.length > 0) {
      const ma5 = chart.addLineSeries({
        color: MA5_COLOR,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ma5.setData(ma5Data);
    }

    const ma20Data = calcMA(bars, 20);
    if (ma20Data.length > 0) {
      const ma20 = chart.addLineSeries({
        color: MA20_COLOR,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ma20.setData(ma20Data);
    }

    chart.timeScale().fitContent();

    // Responsive resize
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && chartRef.current) {
        chartRef.current.applyOptions({ width: w });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [bars, resolvedTheme]);

  return (
    <div className="terminal-card rounded-2xl p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs uppercase tracking-wider text-secondary-text">K线图</span>
          <div className="flex items-center gap-2 text-[10px] text-muted-text">
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-4 rounded" style={{ background: MA5_COLOR }} />
              MA5
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-4 rounded" style={{ background: MA20_COLOR }} />
              MA20
            </span>
          </div>
        </div>

        {/* Period toggle */}
        <div className="flex overflow-hidden rounded-lg border border-subtle text-xs">
          {(['daily', 'weekly'] as Period[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-0.5 transition-colors ${
                period === p
                  ? 'bg-surface text-foreground'
                  : 'text-secondary-text hover:text-foreground'
              }`}
            >
              {p === 'daily' ? '日K' : '周K'}
            </button>
          ))}
        </div>
      </div>

      {/* Chart area */}
      {loading ? (
        <div className="flex h-[300px] items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      ) : !bars || bars.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center text-xs text-muted-text">
          暂无行情数据
        </div>
      ) : (
        <div ref={containerRef} className="h-[300px]" />
      )}
    </div>
  );
};
