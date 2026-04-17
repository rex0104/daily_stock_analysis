# K 线图 AI 标注 & AI 智能选股 Design

> Date: 2026-04-17
> Status: Approved
> Scope: K-line chart AI annotations on existing report view; new AI stock screener page with preset strategies

## 1. Background

The product is a ToC AI-powered stock analysis platform covering A-shares, HK, and US stocks. Two features are being added to increase **conversion** (charts) and **acquisition** (screener):

1. **K-line Chart AI Annotations** — enhance the existing `KLineChart` component with buy/sell markers, support/resistance zones, and trend overlays derived from existing analysis results. Zero additional LLM cost.
2. **AI Stock Screener** — new "Discover" page with 4 preset strategy templates that scan ~5,000 A-shares on-demand, returning candidates with lightweight AI summaries via SSE streaming.

### Current State

- **KLineChart**: `apps/dsa-web/src/components/report/KLineChart.tsx` — lightweight-charts v4.2.3, candlestick + volume + MA5/MA20. No annotations.
- **AnalysisResult**: Contains `buy_point`, `stop_loss`, `target_price`, `trend_prediction`, `sentiment_score`, `operation_advice` fields.
- **Data providers**: 10+ sources with caching layer. Tushare/Baostock/Akshare cover A-shares comprehensively.
- **Frontend stack**: React 19, Tailwind CSS 4, Zustand, Vite 7, Axios, SSE for task streaming.
- **No screener or discovery mechanism exists.**

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Annotation data source | Reuse AnalysisResult fields | Zero extra LLM calls; annotations consistent with report text |
| Support/resistance calculation | Frontend algorithm (MA + high/low points) | Pure math, no backend change needed |
| Trend zone rendering | MA slope + trend_prediction field | Combines quantitative signal with LLM judgment |
| Screener scope | A-shares only | Best data source coverage (Tushare/Baostock/Akshare) |
| Screener mode | Preset strategy templates (4 strategies) | Simple UX, no custom condition builder in v1 |
| Screener execution | On-demand (user-triggered) | Simpler architecture, no batch/cron infrastructure |
| Result AI summaries | Lightweight LLM (1-2 sentences per stock) | Adds value without excessive cost; streamed via SSE |
| Result persistence | None (ephemeral) | Each scan is fresh; no new DB tables for results |
| Screener architecture | Full real-time scan | Simple: one API + one Service + strategy functions; leverages existing data_provider cache |

---

## 2. Feature A: K-line Chart AI Annotations

### 2.1 Data Flow

```
ReportSummary (has analysisResult)
  → extractAnnotations(analysisResult, klineData)
    → priceLines: buy_point, stop_loss, target_price
    → markers: buy arrow on nearest date to buy_point price
    → supportResistance: algorithm(MA20, recent highs/lows)
    → trendZones: parseTrend(trend_prediction) + maSlope(MA20)
  → KLineChart receives annotations prop
  → lightweight-charts renders overlays
```

### 2.2 Annotation Types

| Annotation | Data Source | Rendering | lightweight-charts API |
|------------|------------|-----------|----------------------|
| Buy point | `buy_point` field (price string) | Green up-arrow marker + green dashed horizontal line | `setMarkers()` + `createPriceLine()` |
| Stop loss | `stop_loss` field (price string) | Red dashed horizontal line with label | `createPriceLine()` |
| Target price | `target_price` field (price string) | Gold dashed horizontal line with label | `createPriceLine()` |
| Support zone | Algorithm: lowest of (MA20, min of last 20 candle lows) ± 1% band | Semi-transparent green horizontal band | Custom area series or plugin |
| Resistance zone | Algorithm: highest of (MA20, max of last 20 candle highs) ± 1% band | Semi-transparent red horizontal band | Custom area series or plugin |
| Trend zones | `trend_prediction` keyword mapping + MA20 slope over last 10 bars | Background color blocks: green (uptrend), red (downtrend), gray (sideways) | Chart background coloring via custom plugin |

### 2.3 Price Parsing

The `buy_point`, `stop_loss`, and `target_price` fields in AnalysisResult are strings that may contain labels (e.g., "买入点: 33.20元" or "33.20"). The parser must:

1. Strip non-numeric prefixes/suffixes
2. Extract the first valid float
3. Return `null` if unparseable (annotation not rendered)

Existing `_clean_sniper_value` in the backend does similar work; the frontend parser mirrors this logic.

### 2.4 Support/Resistance Algorithm

```
function calcSupportResistance(klineData, ma20Values):
  recentData = klineData.slice(-20)
  
  // Support: lower bound
  support = min(
    min(recentData.map(d => d.low)),
    ma20Values[ma20Values.length - 1]
  )
  supportBand = [support * 0.99, support * 1.01]
  
  // Resistance: upper bound
  resistance = max(
    max(recentData.map(d => d.high)),
    ma20Values[ma20Values.length - 1]
  )
  resistanceBand = [resistance * 0.99, resistance * 1.01]
  
  return { supportBand, resistanceBand }
```

### 2.5 Trend Zone Algorithm

```
function calcTrendZones(trendPrediction, ma20Values):
  // 1. Parse trend_prediction text for keywords
  trend = parseTrendKeywords(trendPrediction)
  // Keywords: 上涨/看涨/bullish → "up"
  //           下跌/看跌/bearish → "down"
  //           震荡/横盘/sideways → "sideways"
  
  // 2. Confirm with MA20 slope
  slope = (ma20Values[-1] - ma20Values[-10]) / ma20Values[-10]
  if abs(slope) < 0.01:
    trend = "sideways"  // override if MA is flat
  
  return trend  // "up" | "down" | "sideways"
```

### 2.6 UI Changes

**KLineChart.tsx changes:**
- New optional prop: `annotations?: ChartAnnotations`
- Type definition:
  ```typescript
  interface ChartAnnotations {
    buyPoint?: { price: number; date?: string }
    stopLoss?: { price: number }
    targetPrice?: { price: number }
    supportBand?: [number, number]
    resistanceBand?: [number, number]
    trend?: "up" | "down" | "sideways"
  }
  ```
- Toggle button (eye icon) in top-right corner, default ON
- Annotations render after chart data is loaded (useEffect dependency)

**ReportSummary.tsx changes:**
- Import `extractAnnotations` utility
- Pass `annotations` prop to KLineChart when analysisResult is available

### 2.7 Files Changed

| File | Change |
|------|--------|
| `apps/dsa-web/src/components/report/KLineChart.tsx` | Add annotations prop, render price lines / markers / zones, add toggle button |
| `apps/dsa-web/src/components/report/ReportSummary.tsx` | Extract annotations from analysisResult, pass to KLineChart |
| `apps/dsa-web/src/utils/chartAnnotations.ts` | **New file.** Pure functions: `extractAnnotations()`, `parsePrice()`, `calcSupportResistance()`, `calcTrendZones()` |

---

## 3. Feature B: AI Stock Screener

### 3.1 Architecture

```
DiscoverPage (React)
  → POST /api/v1/screener/scan (SSE)
  → screener_service.scan()
    → get_a_share_stock_list() (cached)
    → concurrent fetch daily kline (data_provider cache)
    → strategy function (pure numpy/pandas math)
    → SSE: { type: "candidates", data: [...] }
    → concurrent LLM summaries (LLMToolAdapter)
    → SSE: { type: "summary", code: "600519", summary: "..." }
    → SSE: { type: "done" }
```

### 3.2 Backend: New Files

#### `src/services/screener_strategies.py`

Pure functions, each with the same signature:

```python
def strategy_func(df: pd.DataFrame) -> bool:
    """Return True if the stock matches the strategy criteria.
    
    Args:
        df: DataFrame with columns [date, open, high, low, close, volume]
            sorted by date ascending, at least 60 rows.
    """
```

**4 strategies:**

| Function | ID | Logic |
|----------|-----|-------|
| `trend_breakout(df)` | `trend_breakout` | `close[-1] > MA20[-1]` AND `close[-2] <= MA20[-2]` AND `volume_ratio > 1.5` AND `pct_change_5d < 10%` |
| `oversold_bounce(df)` | `oversold_bounce` | `pct_change_20d < -15%` AND `RSI14 < 30` AND last 3 days has at least 1 green candle or doji |
| `volume_surge(df)` | `volume_surge` | `volume[-1] > volume[-2] > volume[-3]` (3 consecutive volume increases) AND `close[-1] > MA5 > MA10` |
| `ma_bullish(df)` | `ma_bullish` | `MA5 > MA10 > MA20 > MA60` AND `turnover_rate > 2%` |

Strategy registry:

```python
STRATEGIES = {
    "trend_breakout": StrategyDef(id="trend_breakout", name="趋势突破", func=trend_breakout, description="突破MA20+放量，捕捉启动信号"),
    "oversold_bounce": StrategyDef(id="oversold_bounce", name="超跌反弹", func=oversold_bounce, description="20日跌>15%+RSI低，抄底候选"),
    "volume_surge": StrategyDef(id="volume_surge", name="放量上攻", func=volume_surge, description="连续3日放量递增，强势股追踪"),
    "ma_bullish": StrategyDef(id="ma_bullish", name="均线多头", func=ma_bullish, description="MA5>10>20>60，趋势确认"),
}
```

#### `src/services/screener_service.py`

Core orchestration:

```python
class ScreenerService:
    async def scan(self, strategy_id: str, user_id: str) -> AsyncGenerator[ScreenerEvent, None]:
        """
        Yields:
          ScreenerEvent(type="progress", data={"phase": "fetching", "total": N})
          ScreenerEvent(type="candidates", data=[{code, name, price, change_pct, volume_ratio, turnover_rate, pct_5d}, ...])
          ScreenerEvent(type="summary", data={"code": "600519", "summary": "..."})
          ScreenerEvent(type="done", data={"total_scanned": N, "matched": M})
          ScreenerEvent(type="error", data={"message": "..."})
        """
```

Key implementation details:
- Stock list source: Tushare `stock_basic` or Akshare equivalent, cached daily
- Kline data: `data_provider` with existing cache layer, fetch 60-day history per stock
- Concurrency: `asyncio.gather` with semaphore (limit 20 concurrent fetches) for kline data
- Strategy execution: synchronous pandas operations, iterate over candidate DataFrames
- LLM summaries: concurrent via `asyncio.gather` with semaphore (limit 5 concurrent LLM calls)
- Filters: exclude ST stocks, exclude stocks suspended or listed < 60 days

LLM summary prompt:

```
你是一位股票分析师。请用1-2句话简要点评以下股票，基于其命中的筛选策略和近期行情数据。
要求：说明技术面关键信号 + 一个值得关注的点位或风险。

股票：{name}（{code}）
命中策略：{strategy_name}
近5日行情：{recent_5d_summary}
```

#### `api/v1/endpoints/screener.py`

```python
@router.post("/scan")
async def scan_stocks(req: ScreenerScanRequest, user=Depends(get_current_user)):
    """SSE endpoint. Returns streaming screener events."""

@router.get("/strategies")
async def list_strategies():
    """Returns available strategy definitions (id, name, description)."""
```

Schema:

```python
class ScreenerScanRequest(BaseModel):
    strategy: str  # strategy ID

class ScreenerCandidate(BaseModel):
    code: str
    name: str
    price: float
    change_pct: float
    volume_ratio: float
    turnover_rate: float
    pct_5d: float
    summary: Optional[str] = None  # filled async via SSE
```

### 3.3 Frontend: New Files

#### `apps/dsa-web/src/pages/DiscoverPage.tsx`

Page structure:
1. Header: title + data timestamp
2. Strategy cards grid (4 cards, single-select)
3. "Start scan" button (disabled until strategy selected; disabled during scan)
4. Results section: sort dropdown + result list
5. States: empty (no scan yet), scanning (progress), results, error

#### `apps/dsa-web/src/api/screener.ts`

```typescript
export function scanStocks(strategy: string): EventSource
export function listStrategies(): Promise<Strategy[]>
```

SSE event parsing mirrors existing `analysis.ts` SSE pattern.

#### `apps/dsa-web/src/components/screener/StrategyCard.tsx`

Props: `strategy: Strategy`, `selected: boolean`, `onSelect: () => void`
Renders: icon + name + description, selected state with blue border + checkmark.

#### `apps/dsa-web/src/components/screener/ScreenerResultItem.tsx`

Props: `candidate: ScreenerCandidate`, `onAnalyze: (code) => void`, `onAddWatchlist: (code) => void`
Renders: stock info + price + indicators + summary (or spinner) + action buttons.

### 3.4 Navigation

Add to `SidebarNav` (`components/layout/SidebarNav.tsx`):
- Icon: `RiCompass3Line` (from @remixicon/react)
- Label: "发现"
- Position: between Watchlist and Chat
- Route: `/discover`

Add to `App.tsx` router:
- `<Route path="/discover" element={<DiscoverPage />} />`
- Protected route (requires auth)

### 3.5 Mobile Responsiveness

- Strategy cards: 2x2 grid on mobile (from 4x1)
- Result items: stack vertically — name+price row, indicators row, summary row, action buttons row
- Sort dropdown moves to full-width above results

### 3.6 Error Handling

- Data fetch failures for individual stocks: skip silently, do not block scan
- LLM summary failure for individual stocks: show "摘要生成失败" in gray text, do not retry
- SSE connection drop: show "扫描连接中断" with retry button
- No candidates found: show empty state "当前策略未匹配到符合条件的股票"
- Rate limiting: respect existing per-user rate limits

### 3.7 Not In Scope

- Custom condition builder / user-defined filters
- HK / US stock screening
- Result persistence or history
- Scheduled/automated screening
- Push notifications for screener results
- Batch analysis of screener results (user triggers one at a time via "分析" button)

---

## 4. Files Summary

### New Files

| File | Feature |
|------|---------|
| `apps/dsa-web/src/utils/chartAnnotations.ts` | A: annotation extraction + algorithms |
| `src/services/screener_service.py` | B: screener orchestration |
| `src/services/screener_strategies.py` | B: 4 preset strategy functions |
| `api/v1/endpoints/screener.py` | B: SSE scan + list strategies endpoints |
| `apps/dsa-web/src/pages/DiscoverPage.tsx` | B: discover page |
| `apps/dsa-web/src/api/screener.ts` | B: API module |
| `apps/dsa-web/src/components/screener/StrategyCard.tsx` | B: strategy card component |
| `apps/dsa-web/src/components/screener/ScreenerResultItem.tsx` | B: result item component |

### Modified Files

| File | Feature | Change |
|------|---------|--------|
| `apps/dsa-web/src/components/report/KLineChart.tsx` | A | Add annotations prop + rendering + toggle |
| `apps/dsa-web/src/components/report/ReportSummary.tsx` | A | Extract and pass annotations |
| `apps/dsa-web/src/App.tsx` | B | Add /discover route |
| `apps/dsa-web/src/components/layout/SidebarNav.tsx` | B | Add "发现" nav item |
| `api/v1/router.py` (or equivalent) | B | Register screener router |
