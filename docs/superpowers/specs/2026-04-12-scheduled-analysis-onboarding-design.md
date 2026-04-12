# Scheduled Watchlist Analysis + New User Onboarding Design

> Date: 2026-04-12
> Status: Approved
> Scope: Per-user scheduled analysis with personal notifications, 3-step onboarding wizard

## 1. Feature A: Per-User Scheduled Watchlist Analysis

### Goal

Each user can configure "auto-analyze my watchlist daily at HH:MM" and receive results on their own notification channels.

### Data Model

**`users` table — add columns (migration v4):**

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| schedule_enabled | Boolean | false | Whether auto-analysis is on |
| schedule_time | String(5) | "09:15" | HH:MM in user's intent (market-aware) |
| onboarding_completed | Boolean | false | Whether user finished the onboarding wizard |

No new tables needed — schedule config lives on the user record.

### Backend

**Scheduler changes (`src/core/scheduler.py` or equivalent):**

The existing scheduler runs a global job based on `SCHEDULE_TIME` env var. For multi-user:

1. At each minute tick, query `users WHERE schedule_enabled = true AND schedule_time = current_HH:MM`
2. For each matching user:
   a. Load their watchlist (`user_watchlists`)
   b. Load their settings (`users.settings` JSON) → inject into environment
   c. Create a `StockAnalysisPipeline(user_id=user.id)` for each stock
   d. Send notifications using the user's configured channels

**New service: `src/services/user_schedule_service.py`:**

```python
class UserScheduleService:
    def update_schedule(self, user_id, enabled, time) -> dict
    def get_schedule(self, user_id) -> dict
    def get_due_users(self, hhmm: str) -> List[dict]  # users due at this time
    def run_user_analysis(self, user_id: str) -> dict  # analyze all watchlist stocks
```

**API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/schedule` | Get current user's schedule config |
| PUT | `/api/v1/schedule` | Update schedule: `{enabled, time}` |

### Notification routing

When analyzing for a specific user, notifications must use **that user's** configured channels (from their `users.settings` JSON), not the global `.env`. 

The `run_user_analysis` method:
1. Read user's settings from DB
2. Temporarily set env vars from user settings
3. Initialize NotificationService with user's channel config
4. Run analysis pipeline for each watchlist stock
5. Send consolidated report via user's channels
6. Restore env vars

### Frontend

- **Settings page** new section: "定时分析"
  - Toggle: "每日自动分析自选股"
  - Time picker: HH:MM
  - Status: "下次分析时间: 明天 09:15" or "未开启"
- **Watchlist page** header: show schedule status badge ("每日 09:15 自动分析" or "未开启定时")

---

## 2. Feature B: New User Onboarding Wizard

### Goal

After registration, guide user through 3 steps to reach first value (receive an analysis report). Only require the minimum config to run: one LLM API key.

### Onboarding Steps

**Step 1: Configure AI Model (required)**
- Headline: "配置 AI 模型"
- Show 3-4 popular provider options as cards:
  - Gemini (free tier available)
  - DeepSeek
  - OpenAI / compatible
  - AIHubMix (recommended, one key for all)
- User picks one, enters API Key
- "测试连接" button → calls existing `/api/v1/system/config/llm/test-channel` 
- Green checkmark on success → can proceed

**Step 2: Add Stocks (required, at least 1)**
- Headline: "添加感兴趣的股票"
- StockAutocomplete search input (reuse existing component)
- Show popular/trending suggestions: "贵州茅台 600519", "AAPL", "腾讯 hk00700"
- User adds 1+ stocks → shown as chips below
- These get saved to watchlist via existing API

**Step 3: First Analysis + Optional Notification**
- Headline: "开始第一次分析"
- "立即分析" button → triggers analysis for all added stocks
- While analyzing: show progress
- After complete: show summary card with result preview
- Below: optional "配置通知推送" accordion (Telegram/WeChat/Email quick setup)
- "完成设置" button → marks onboarding complete

### Data Model

`users.onboarding_completed` (Boolean, default false) — added in migration v4 alongside schedule columns.

### Backend

**API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/onboarding/status` | Get onboarding progress |
| POST | `/api/v1/onboarding/complete` | Mark onboarding as done |

Onboarding status is derived from:
- `has_llm_key`: check if user's settings have any LLM API key configured
- `has_watchlist`: check if user has 1+ watchlist items
- `has_analysis`: check if user has 1+ analysis_history records
- `completed`: `users.onboarding_completed`

### Frontend

**New component: `apps/dsa-web/src/components/onboarding/OnboardingWizard.tsx`**

- Full-page overlay (like login page styling)
- 3-step stepper at top
- Each step is a self-contained card
- Progress persists — user can close and resume
- After all 3 steps: confetti/celebration → redirect to home

**App.tsx routing:**
- After login, if `onboarding_completed === false`, redirect to `/onboarding`
- `/onboarding` route renders OnboardingWizard
- User can skip via small "跳过引导" link (marks complete without finishing)

### LLM Provider Quick Setup (Step 1 detail)

For each provider, show:
- Provider logo/name
- What to fill: just the API Key field
- Link to "获取 Key" (opens provider's console in new tab)
- The field maps to the correct env key:
  - Gemini → `GEMINI_API_KEY`
  - DeepSeek → `OPENAI_API_KEY` + `OPENAI_BASE_URL=https://api.deepseek.com/v1` + `OPENAI_MODEL=deepseek-chat`
  - OpenAI → `OPENAI_API_KEY`
  - AIHubMix → `AIHUBMIX_KEY`

Save via existing `/api/v1/system/config` endpoint (user-scoped).

---

## 3. Files

### Backend create
- `src/services/user_schedule_service.py` — schedule CRUD + due-user query + run analysis
- `api/v1/endpoints/schedule.py` — schedule GET/PUT
- `api/v1/endpoints/onboarding.py` — onboarding status/complete

### Backend modify
- `src/storage.py` — User model add `schedule_enabled`, `schedule_time`, `onboarding_completed`
- `src/migration.py` — v4 migration
- `api/v1/router.py` — register new routers
- Scheduler integration (existing scheduler module) — add per-user job dispatch

### Frontend create
- `apps/dsa-web/src/pages/OnboardingPage.tsx` — wizard page
- `apps/dsa-web/src/components/onboarding/StepLLMSetup.tsx` — step 1
- `apps/dsa-web/src/components/onboarding/StepAddStocks.tsx` — step 2
- `apps/dsa-web/src/components/onboarding/StepFirstAnalysis.tsx` — step 3
- `apps/dsa-web/src/api/onboarding.ts` — API client
- `apps/dsa-web/src/api/schedule.ts` — API client

### Frontend modify
- `apps/dsa-web/src/App.tsx` — onboarding redirect
- `apps/dsa-web/src/contexts/AuthContext.tsx` — add `onboardingCompleted` to status
- `apps/dsa-web/src/pages/SettingsPage.tsx` — add schedule section
- `apps/dsa-web/src/pages/WatchlistPage.tsx` — show schedule status badge
