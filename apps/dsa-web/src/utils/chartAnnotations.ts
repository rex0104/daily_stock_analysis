/**
 * Chart annotation utilities.
 *
 * Pure functions that extract and compute chart overlay data from analysis
 * report fields. These functions are designed to be side-effect-free and
 * easily testable.
 */

import type { ReportStrategy, ReportSummary } from '../types/analysis';
import type { KlineBar } from '../api/stocks';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Trend = 'up' | 'down' | 'sideways';

export interface SupportResistance {
  supportCenter: number;
  supportLow: number;
  supportHigh: number;
  resistanceCenter: number;
  resistanceLow: number;
  resistanceHigh: number;
}

export interface ChartAnnotations {
  buyPoint?: number;
  stopLoss?: number;
  targetPrice?: number;
  support?: SupportResistance;
  trend: Trend;
}

// ---------------------------------------------------------------------------
// parsePrice
// ---------------------------------------------------------------------------

/**
 * Extract the first valid number from a strategy price string.
 *
 * Handles plain numbers ("33.20"), labelled strings ("买入点: 33.20元"),
 * and range strings ("33.00-34.50" → 33.00). Returns null for
 * empty/undefined/non-numeric input.
 */
export function parsePrice(value: string | undefined | null): number | null {
  if (value == null) return null;
  const trimmed = value.trim();
  if (trimmed === '') return null;

  // Match the first occurrence of an optional leading minus followed by digits
  // and an optional decimal part. We intentionally avoid matching a leading
  // minus that is a range separator (e.g. "33.00-34.50"), so we anchor the
  // pattern to digits or the very start of the number token.
  const match = trimmed.match(/\d+(?:\.\d+)?/);
  if (!match) return null;

  const num = Number(match[0]);
  return Number.isFinite(num) ? num : null;
}

// ---------------------------------------------------------------------------
// calcSupportResistance
// ---------------------------------------------------------------------------

/**
 * Compute support and resistance bands from recent K-line data and the MA20.
 *
 * - Returns null when fewer than 5 bars are provided.
 * - Uses up to the most recent 20 bars.
 * - Support  = min(recent bar lows,  ma20)  ± 1%
 * - Resistance = max(recent bar highs, ma20) ± 1%
 */
export function calcSupportResistance(
  bars: Pick<KlineBar, 'low' | 'high'>[],
  ma20: number,
): SupportResistance | null {
  if (bars.length < 5) return null;

  const recent = bars.slice(-20);
  const minLow = Math.min(...recent.map((b) => b.low));
  const maxHigh = Math.max(...recent.map((b) => b.high));

  const supportCenter = Math.min(minLow, ma20);
  const resistanceCenter = Math.max(maxHigh, ma20);

  return {
    supportCenter,
    supportLow: supportCenter * 0.99,
    supportHigh: supportCenter * 1.01,
    resistanceCenter,
    resistanceLow: resistanceCenter * 0.99,
    resistanceHigh: resistanceCenter * 1.01,
  };
}

// ---------------------------------------------------------------------------
// determineTrend
// ---------------------------------------------------------------------------

/**
 * Determine chart trend from LLM trend text and an array of MA20 values.
 *
 * MA slope is calculated as (last − first) / first using the first and last
 * elements of `ma20Values`. When the absolute slope is less than 1%, the
 * function forces "sideways" regardless of text content.
 *
 * Keyword priority (highest first):
 *   1. Sideways: 震荡 | 横盘
 *   2. Bullish:  上涨 | 看涨 | bullish
 *   3. Bearish:  下跌 | 看跌 | bearish
 *   4. Default:  "sideways"
 */
export function determineTrend(
  trendPrediction: string,
  ma20Values: number[],
): Trend {
  // Cannot compute slope with fewer than 2 points.
  if (ma20Values.length < 2) return 'sideways';

  const first = ma20Values[0];
  const last = ma20Values[ma20Values.length - 1];
  const slope = first === 0 ? 0 : Math.abs((last - first) / first);

  if (slope < 0.01) return 'sideways';

  const text = trendPrediction.toLowerCase();

  // Sideways keywords take precedence over bullish/bearish.
  if (text.includes('震荡') || text.includes('横盘')) return 'sideways';

  if (text.includes('上涨') || text.includes('看涨') || text.includes('bullish')) return 'up';
  if (text.includes('下跌') || text.includes('看跌') || text.includes('bearish')) return 'down';

  return 'sideways';
}

// ---------------------------------------------------------------------------
// extractAnnotations
// ---------------------------------------------------------------------------

/**
 * Main entry point: combine all annotation utilities into a single
 * ChartAnnotations object suitable for rendering on a K-line chart.
 *
 * @param strategy  Report strategy section (idealBuy, secondaryBuy, stopLoss, takeProfit)
 * @param summary   Report summary section (trendPrediction)
 * @param bars      Full array of K-line bars for the stock
 * @param ma20Values Array of MA20 values (chronological order)
 */
export function extractAnnotations(
  strategy: ReportStrategy,
  summary: ReportSummary,
  bars: KlineBar[],
  ma20Values: number[],
): ChartAnnotations {
  // Buy point: prefer idealBuy, fall back to secondaryBuy.
  const rawBuyPoint =
    parsePrice(strategy.idealBuy) ?? parsePrice(strategy.secondaryBuy) ?? undefined;

  const stopLoss = parsePrice(strategy.stopLoss) ?? undefined;
  const targetPrice = parsePrice(strategy.takeProfit) ?? undefined;

  // MA20 for support/resistance: use last value in the series.
  const ma20 = ma20Values.length > 0 ? ma20Values[ma20Values.length - 1] : 0;
  const support = calcSupportResistance(bars, ma20) ?? undefined;

  const trend = determineTrend(summary.trendPrediction, ma20Values);

  return {
    ...(rawBuyPoint !== undefined ? { buyPoint: rawBuyPoint } : {}),
    ...(stopLoss !== undefined ? { stopLoss } : {}),
    ...(targetPrice !== undefined ? { targetPrice } : {}),
    ...(support !== undefined ? { support } : {}),
    trend,
  };
}
