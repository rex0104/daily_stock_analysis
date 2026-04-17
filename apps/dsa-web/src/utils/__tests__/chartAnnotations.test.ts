import { describe, it, expect } from 'vitest';
import {
  parsePrice,
  calcSupportResistance,
  determineTrend,
  extractAnnotations,
} from '../chartAnnotations';
import type { ReportStrategy, ReportSummary } from '../../types/analysis';
import type { KlineBar } from '../../api/stocks';

// ---------------------------------------------------------------------------
// parsePrice
// ---------------------------------------------------------------------------

describe('parsePrice', () => {
  it('returns null for undefined', () => {
    expect(parsePrice(undefined)).toBeNull();
  });

  it('returns null for null', () => {
    expect(parsePrice(null)).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(parsePrice('')).toBeNull();
  });

  it('returns null for non-numeric string', () => {
    expect(parsePrice('abc')).toBeNull();
  });

  it('parses a plain number string', () => {
    expect(parsePrice('33.20')).toBe(33.20);
  });

  it('parses a number with Chinese label prefix', () => {
    expect(parsePrice('买入点: 33.20元')).toBe(33.20);
  });

  it('takes the first number from a range string', () => {
    expect(parsePrice('33.00-34.50')).toBe(33.00);
  });

  it('parses an integer string', () => {
    expect(parsePrice('100')).toBe(100);
  });

  it('returns null for whitespace-only string', () => {
    expect(parsePrice('   ')).toBeNull();
  });

  it('parses number embedded in mixed text', () => {
    expect(parsePrice('目标价 55.50 元附近')).toBe(55.50);
  });
});

// ---------------------------------------------------------------------------
// calcSupportResistance
// ---------------------------------------------------------------------------

function makeBars(lows: number[], highs: number[]): KlineBar[] {
  return lows.map((low, i) => ({
    date: `2024-01-${String(i + 1).padStart(2, '0')}`,
    open: low + 1,
    high: highs[i],
    low,
    close: low + 1,
    volume: null,
  }));
}

describe('calcSupportResistance', () => {
  it('returns null when fewer than 5 bars', () => {
    const bars = makeBars([10, 11, 12, 13], [20, 21, 22, 23]);
    expect(calcSupportResistance(bars, 15)).toBeNull();
  });

  it('returns null for empty bars array', () => {
    expect(calcSupportResistance([], 15)).toBeNull();
  });

  it('computes support and resistance for exactly 5 bars', () => {
    const lows = [10, 9, 11, 8, 10];
    const highs = [20, 21, 19, 22, 20];
    const bars = makeBars(lows, highs);
    const ma20 = 15;
    const result = calcSupportResistance(bars, ma20);
    expect(result).not.toBeNull();
    // Support center = min(min(lows), ma20) = min(8, 15) = 8
    expect(result!.supportCenter).toBe(8);
    expect(result!.supportLow).toBeCloseTo(8 * 0.99, 5);
    expect(result!.supportHigh).toBeCloseTo(8 * 1.01, 5);
    // Resistance center = max(max(highs), ma20) = max(22, 15) = 22
    expect(result!.resistanceCenter).toBe(22);
    expect(result!.resistanceLow).toBeCloseTo(22 * 0.99, 5);
    expect(result!.resistanceHigh).toBeCloseTo(22 * 1.01, 5);
  });

  it('only considers the most recent 20 bars when more are provided', () => {
    // 25 bars: first 5 have extreme lows/highs that should be ignored
    const lows = [
      1, 1, 1, 1, 1, // old bars (ignored)
      10, 9, 11, 8, 10, 10, 9, 11, 8, 10,
      10, 9, 11, 8, 10, 10, 9, 11, 8, 10,
    ];
    const highs = [
      100, 100, 100, 100, 100, // old bars (ignored)
      20, 21, 19, 22, 20, 20, 21, 19, 22, 20,
      20, 21, 19, 22, 20, 20, 21, 19, 22, 20,
    ];
    const bars = makeBars(lows, highs);
    const ma20 = 15;
    const result = calcSupportResistance(bars, ma20);
    expect(result).not.toBeNull();
    // Recent 20 lows: min = 8; ma20 = 15 → support center = 8
    expect(result!.supportCenter).toBe(8);
    // Recent 20 highs: max = 22; ma20 = 15 → resistance center = 22
    expect(result!.resistanceCenter).toBe(22);
  });

  it('uses ma20 when it is lower than bar lows (support)', () => {
    const lows = [20, 21, 22, 23, 24];
    const highs = [30, 31, 32, 33, 34];
    const bars = makeBars(lows, highs);
    const ma20 = 10; // lower than all lows → support center = 10
    const result = calcSupportResistance(bars, ma20);
    expect(result).not.toBeNull();
    expect(result!.supportCenter).toBe(10);
  });

  it('uses ma20 when it is higher than bar highs (resistance)', () => {
    const lows = [10, 11, 12, 13, 14];
    const highs = [20, 21, 22, 23, 24];
    const bars = makeBars(lows, highs);
    const ma20 = 50; // higher than all highs → resistance center = 50
    const result = calcSupportResistance(bars, ma20);
    expect(result).not.toBeNull();
    expect(result!.resistanceCenter).toBe(50);
  });
});

// ---------------------------------------------------------------------------
// determineTrend
// ---------------------------------------------------------------------------

describe('determineTrend', () => {
  it('returns "sideways" when ma20Values has fewer than 2 elements', () => {
    expect(determineTrend('上涨', [])).toBe('sideways');
    expect(determineTrend('上涨', [10])).toBe('sideways');
  });

  it('forces "sideways" when MA slope is below 1%', () => {
    // slope = (10.05 - 10) / 10 = 0.5% < 1%
    expect(determineTrend('上涨', [10, 10.05])).toBe('sideways');
  });

  it('returns "up" when MA slope >= 1% and text contains 上涨', () => {
    expect(determineTrend('上涨明显', [10, 11])).toBe('up');
  });

  it('returns "up" for 看涨 keyword', () => {
    expect(determineTrend('整体看涨', [10, 11])).toBe('up');
  });

  it('returns "up" for bullish keyword', () => {
    expect(determineTrend('market is bullish', [10, 11])).toBe('up');
  });

  it('returns "down" for 下跌 keyword', () => {
    expect(determineTrend('下跌趋势', [10, 9])).toBe('down');
  });

  it('returns "down" for 看跌 keyword', () => {
    expect(determineTrend('市场看跌', [10, 9])).toBe('down');
  });

  it('returns "down" for bearish keyword', () => {
    expect(determineTrend('trend is bearish', [10, 9])).toBe('down');
  });

  it('returns "sideways" for 震荡 keyword even with high slope', () => {
    expect(determineTrend('震荡行情', [10, 11])).toBe('sideways');
  });

  it('returns "sideways" for 横盘 keyword even with high slope', () => {
    expect(determineTrend('横盘整理', [10, 11])).toBe('sideways');
  });

  it('defaults to "sideways" when no keyword matches', () => {
    expect(determineTrend('无明显趋势', [10, 11])).toBe('sideways');
  });

  it('sideways keywords take precedence over bullish keywords', () => {
    expect(determineTrend('震荡看涨', [10, 11])).toBe('sideways');
  });

  it('uses first and last ma20 values for slope calculation', () => {
    // 5-element array: first=10, last=12 → slope = (12-10)/10 = 20% >= 1%
    expect(determineTrend('上涨', [10, 10.1, 10.5, 11, 12])).toBe('up');
  });

  it('returns "sideways" when long array trends up overall but last 10 are flat', () => {
    // 30 values: first 20 rise strongly from 10 to 20, last 10 are flat around 20
    const rising = Array.from({ length: 20 }, (_, i) => 10 + i * 0.5); // 10..19.5
    const flat = Array.from({ length: 10 }, () => 20);                  // 20..20
    const ma20Values = [...rising, ...flat];
    // Overall slope is huge, but last 10 window: first=20, last=20 → slope=0% < 1%
    expect(determineTrend('上涨', ma20Values)).toBe('sideways');
  });

  it('returns "sideways" when first MA20 value in the window is 0', () => {
    // window[0] === 0 → slope guard triggers → sideways
    expect(determineTrend('上涨', [0, 5])).toBe('sideways');
  });
});

// ---------------------------------------------------------------------------
// extractAnnotations
// ---------------------------------------------------------------------------

const baseBars: KlineBar[] = makeBars(
  [10, 9, 11, 8, 10, 10, 9, 11, 8, 10],
  [20, 21, 19, 22, 20, 20, 21, 19, 22, 20],
);

const baseSummary: ReportSummary = {
  analysisSummary: '',
  operationAdvice: '',
  trendPrediction: '上涨趋势',
  sentimentScore: 70,
};

describe('extractAnnotations', () => {
  it('returns trend "sideways" when ma20Values has flat slope', () => {
    const strategy: ReportStrategy = {};
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 10.05]);
    expect(result.trend).toBe('sideways');
  });

  it('returns trend "up" when slope >= 1% and text is bullish', () => {
    const strategy: ReportStrategy = {};
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.trend).toBe('up');
  });

  it('extracts buyPoint from idealBuy', () => {
    const strategy: ReportStrategy = { idealBuy: '买入点: 33.20元' };
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.buyPoint).toBe(33.20);
  });

  it('falls back to secondaryBuy when idealBuy is missing', () => {
    const strategy: ReportStrategy = { secondaryBuy: '30.00-31.00' };
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.buyPoint).toBe(30.00);
  });

  it('prefers idealBuy over secondaryBuy', () => {
    const strategy: ReportStrategy = { idealBuy: '35.00', secondaryBuy: '30.00' };
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.buyPoint).toBe(35.00);
  });

  it('leaves buyPoint undefined when neither idealBuy nor secondaryBuy parses', () => {
    const strategy: ReportStrategy = { idealBuy: 'N/A', secondaryBuy: '' };
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.buyPoint).toBeUndefined();
  });

  it('extracts stopLoss', () => {
    const strategy: ReportStrategy = { stopLoss: '28.00元' };
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.stopLoss).toBe(28.00);
  });

  it('extracts targetPrice from takeProfit', () => {
    const strategy: ReportStrategy = { takeProfit: '目标价 55.50 元附近' };
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.targetPrice).toBe(55.50);
  });

  it('includes support/resistance when bars >= 5', () => {
    const strategy: ReportStrategy = {};
    const result = extractAnnotations(strategy, baseSummary, baseBars, [10, 11]);
    expect(result.support).not.toBeUndefined();
    expect(result.support!.supportCenter).toBe(8);
    expect(result.support!.resistanceCenter).toBe(22);
  });

  it('omits support/resistance when bars < 5', () => {
    const fewBars = makeBars([10, 11], [20, 21]);
    const strategy: ReportStrategy = {};
    const result = extractAnnotations(strategy, baseSummary, fewBars, [10, 11]);
    expect(result.support).toBeUndefined();
  });

  it('returns trend "sideways" when ma20Values is empty', () => {
    const strategy: ReportStrategy = {};
    const result = extractAnnotations(strategy, baseSummary, baseBars, []);
    expect(result.trend).toBe('sideways');
  });
});
