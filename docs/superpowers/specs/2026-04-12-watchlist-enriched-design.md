# Watchlist Page Enhancement Design

> Date: 2026-04-12
> Status: Approved
> Scope: Enriched watchlist with price, analysis, sparkline, groups, sort, history timeline

## 1. Goal

Transform the watchlist page from a simple favorites list into a personal dashboard showing real-time prices, AI analysis summaries, sparkline charts, custom groups, and analysis history timeline.

## 2. Data Model Changes

### Migration v3: `user_watchlists` additions

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| group_id | String(32) | `"default"` | Group this stock belongs to |
| sort_order | Integer | `0` | Sort within group (lower = first) |

### New table: `user_watchlist_groups`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | String(32) | PK | UUID hex |
| user_id | String(32) | NOT NULL, INDEX | FK → users.id |
| name | String(50) | NOT NULL | Group name (e.g. "重仓", "观察") |
| sort_order | Integer | default 0 | Group display order |
| created_at | DateTime | NOT NULL | |

Unique constraint: `(user_id, name)`

Every user implicitly has a "默认" group with `id="default"` — not stored in DB, handled in code.

## 3. API

### `GET /api/v1/watchlist/enriched`

Returns the full enriched watchlist grouped by category.

Response:
```json
{
  "groups": [
    {
      "group_id": "default",
      "group_name": "默认",
      "sort_order": 0,
      "items": [
        {
          "stock_code": "600519",
          "stock_name": "贵州茅台",
          "group_id": "default",
          "sort_order": 0,
          "market": "cn",
          "price": { "close": 1680.0, "pct_chg": -1.23 },
          "analysis": {
            "sentiment_score": 82,
            "operation_advice": "持有",
            "analysis_summary": "均线多头排列...",
            "analyzed_at": "2026-04-11T10:30:00"
          },
          "position": {
            "quantity": 100,
            "avg_cost": 1620.0,
            "market_value": 168000.0,
            "unrealized_pnl": 6000.0,
            "pnl_pct": 3.7
          },
          "sparkline": [1650.0, 1660.0, 1680.0],
          "history_timeline": [
            {"date": "2026-04-11", "sentiment_score": 82, "operation_advice": "持有"},
            {"date": "2026-04-08", "sentiment_score": 75, "operation_advice": "观望"}
          ]
        }
      ]
    }
  ]
}
```

Backend logic:
1. Read `user_watchlists` + `user_watchlist_groups` for the user
2. Batch query `stock_daily` last 30 rows per stock (sparkline + latest close/pct_chg)
3. Batch query `analysis_history` last 5 per stock for the user (summary + timeline)
4. Batch query `portfolio_positions` for user's accounts (via `portfolio_accounts.owner_id`) — match by symbol to attach holding info
5. Infer market from stock code prefix
6. Group items by group_id, sort groups and items by sort_order

`position` field is `null` when the stock is not held in any portfolio account. When held across multiple accounts, sum the quantities and compute weighted avg cost.

### `PUT /api/v1/watchlist/reorder`

Batch update sort_order and group_id for watchlist items.

Request: `{ "items": [{ "stockCode": "600519", "sortOrder": 0, "groupId": "default" }] }`

### `POST /api/v1/watchlist/groups`

Create a group. Request: `{ "name": "重仓" }`. Returns the group object.

### `PUT /api/v1/watchlist/groups/{group_id}`

Rename a group. Request: `{ "name": "新名称" }`.

### `DELETE /api/v1/watchlist/groups/{group_id}`

Delete a group. Items in it move to "default" group.

## 4. Market Detection

From stock code prefix:
- Starts with `hk` → `hk` (Hong Kong)
- 6-digit numeric → `cn` (A-share)
- Otherwise → `us` (US stock)

## 5. Frontend

### Card layout

Each stock is a card in a responsive grid (1/2/3 cols). Card contains:
- Stock name + code
- Latest price + change % (red up / green down, per existing `--home-price-up/down` tokens)
- 30-day sparkline (SVG polyline, ~40px height, colored by trend)
- Sentiment score dot + operation advice badge
- Position badge (if held): "持仓 100股 +3.7%" with green/red coloring
- Click to expand → analysis history timeline (last 5 analyses as dots/chips)
- Action buttons: analyze, move group (dropdown), remove

### Page header

- `PageHeader` with title "我的自选"
- `StockAutocomplete` inline for adding stocks directly
- "+ 新分组" button

### Groups

- Each group is a collapsible section with header: "▼ {name} ({count})"
- Drag or arrow buttons to reorder items within a group
- Group management: rename (inline edit), delete (confirm dialog)

### Sparkline component

New `<Sparkline data={number[]} />` component:
- SVG polyline, width 100%, height 40px
- Color: green if last > first, red if last < first, muted if equal
- No axes, no labels — just the line

### History timeline (expanded card)

Horizontal row of chips showing last 5 analyses:
- Each chip: date + sentiment emoji + advice label
- Color-coded by sentiment (cyan for bullish, red for bearish, purple for neutral)

## 6. Files

### Backend create
- `src/services/watchlist_enrichment_service.py` — enriched query logic
- `api/v1/endpoints/watchlist.py` — add new endpoints to existing router

### Backend modify
- `src/storage.py` — add `UserWatchlistGroup` model, add columns to `UserWatchlist`
- `src/migration.py` — v3 migration
- `src/services/watchlist_service.py` — add group CRUD, reorder, enriched data

### Frontend create
- `apps/dsa-web/src/components/watchlist/WatchlistCard.tsx` — enriched stock card
- `apps/dsa-web/src/components/watchlist/Sparkline.tsx` — SVG sparkline
- `apps/dsa-web/src/components/watchlist/HistoryTimeline.tsx` — analysis history chips
- `apps/dsa-web/src/components/watchlist/GroupSection.tsx` — collapsible group
- `apps/dsa-web/src/components/watchlist/AddStockInput.tsx` — inline StockAutocomplete wrapper

### Frontend modify
- `apps/dsa-web/src/pages/WatchlistPage.tsx` — full rewrite with enriched data
- `apps/dsa-web/src/api/watchlist.ts` — add enriched/group/reorder endpoints
