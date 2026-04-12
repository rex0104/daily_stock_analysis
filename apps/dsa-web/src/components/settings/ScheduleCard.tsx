import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { scheduleApi, type ScheduleConfig } from '../../api/schedule';
import { Button } from '../common';
import { SettingsAlert } from './SettingsAlert';
import { SettingsSectionCard } from './SettingsSectionCard';

function getNextAnalysisLabel(time: string): string {
  const now = new Date();
  const [hStr, mStr] = time.split(':');
  const h = parseInt(hStr ?? '9', 10);
  const m = parseInt(mStr ?? '0', 10);
  const next = new Date(now);
  next.setHours(h, m, 0, 0);
  if (next <= now) {
    next.setDate(next.getDate() + 1);
  }
  const isToday =
    next.getDate() === now.getDate() &&
    next.getMonth() === now.getMonth() &&
    next.getFullYear() === now.getFullYear();
  return isToday ? `今天 ${time}` : `明天 ${time}`;
}

export const ScheduleCard: React.FC = () => {
  const [config, setConfig] = useState<ScheduleConfig>({ enabled: false, time: '09:15' });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [runSuccess, setRunSuccess] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    scheduleApi
      .get()
      .then((data) => {
        if (!cancelled) setConfig(data);
      })
      .catch(() => {
        // silently ignore load failure — card shows defaults
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const saveConfig = useCallback(async (next: ScheduleConfig) => {
    setSaveError(null);
    setIsSaving(true);
    try {
      const saved = await scheduleApi.update(next);
      setConfig(saved);
    } catch {
      setSaveError('保存失败，请重试');
    } finally {
      setIsSaving(false);
    }
  }, []);

  const scheduleDebounced = useCallback(
    (next: ScheduleConfig) => {
      if (debounceRef.current !== null) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        void saveConfig(next);
      }, 600);
    },
    [saveConfig],
  );

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = { ...config, time: e.target.value };
    setConfig(next);
    scheduleDebounced(next);
  };

  const handleRunNow = async () => {
    setRunError(null);
    setRunSuccess(false);
    setIsRunning(true);
    try {
      await scheduleApi.runNow();
      setRunSuccess(true);
      setTimeout(() => setRunSuccess(false), 4000);
    } catch {
      setRunError('触发失败，请重试');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <SettingsSectionCard
      title="定时分析"
      description="配置每日自动分析自选股的时间，也可立即触发一次分析。"
    >
      <div className="space-y-5">
        {/* Toggle row */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-foreground">每日自动分析</p>
            <p className="text-xs text-muted-text">开启后每天在指定时间自动分析自选股</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={config.enabled}
            disabled={isLoading || isSaving}
            onClick={() => {
              const next = { ...config, enabled: !config.enabled };
              setConfig(next);
              scheduleDebounced(next);
            }}
            className={[
              'relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200',
              'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-cyan/20',
              'disabled:cursor-not-allowed disabled:opacity-50',
              config.enabled
                ? 'bg-cyan'
                : 'bg-border/60',
            ].join(' ')}
          >
            <span
              className={[
                'pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-md ring-0 transition-transform duration-200',
                config.enabled ? 'translate-x-5' : 'translate-x-0',
              ].join(' ')}
            />
          </button>
        </div>

        {/* Time input */}
        <div className="flex items-center gap-3">
          <label
            htmlFor="schedule-time"
            className="min-w-[4rem] text-sm font-medium text-foreground"
          >
            分析时间
          </label>
          <input
            id="schedule-time"
            type="time"
            value={config.time}
            onChange={handleTimeChange}
            disabled={isLoading || isSaving || !config.enabled}
            className={[
              'rounded-xl border px-3 py-1.5 text-sm font-mono text-foreground',
              'bg-background/60 transition-colors',
              'border-[var(--settings-input-rest-border)]',
              'focus:outline-none focus:ring-2 focus:ring-cyan/25',
              'disabled:cursor-not-allowed disabled:opacity-50',
            ].join(' ')}
          />
        </div>

        {/* Run now button */}
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="settings-secondary"
            onClick={() => void handleRunNow()}
            disabled={isLoading || isRunning}
            isLoading={isRunning}
            loadingText="触发中..."
          >
            立即执行一次
          </Button>
        </div>

        {/* Status line */}
        <p className="text-xs text-muted-text">
          {isLoading
            ? '加载中...'
            : config.enabled
              ? `状态：下次分析 ${getNextAnalysisLabel(config.time)}`
              : '状态：未开启定时分析'}
        </p>

        {/* Feedback */}
        {saveError ? (
          <SettingsAlert title="保存失败" message={saveError} variant="error" />
        ) : null}
        {runError ? (
          <SettingsAlert title="触发失败" message={runError} variant="error" />
        ) : null}
        {runSuccess ? (
          <SettingsAlert title="已触发" message="分析任务已在后台启动。" variant="success" />
        ) : null}
      </div>
    </SettingsSectionCard>
  );
};
