import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { shareApi, type SharedReport } from '../api/share';
import { Loading } from '../components/common';

const SharePage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [report, setReport] = useState<SharedReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!token) {
      setNotFound(true);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    const fetchReport = async () => {
      try {
        const data = await shareApi.get(token);
        if (!cancelled) {
          setReport(data);
          document.title = `${data.brandName} - ${data.stockName} 分析报告`;
        }
      } catch {
        if (!cancelled) {
          setNotFound(true);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void fetchReport();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-base">
        <Loading label="加载分析报告中..." />
      </div>
    );
  }

  if (notFound || !report) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-base px-4">
        <div className="terminal-card rounded-2xl p-8 text-center max-w-md w-full">
          <p className="text-4xl mb-4">404</p>
          <h1 className="text-xl font-semibold text-foreground mb-2">分享链接无效或已过期</h1>
          <p className="text-sm text-secondary-text mb-6">该分析报告的分享链接不存在，或已被撤回。</p>
          <Link
            to="/login"
            className="btn-primary inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm"
          >
            登录查看更多分析
          </Link>
        </div>
      </div>
    );
  }

  const sentimentColor =
    report.sentimentScore === null
      ? 'text-secondary-text'
      : report.sentimentScore <= 20
        ? 'text-red-500'
        : report.sentimentScore <= 40
          ? 'text-orange-500'
          : report.sentimentScore <= 60
            ? 'text-yellow-500'
            : report.sentimentScore <= 80
              ? 'text-green-500'
              : 'text-emerald-500';

  return (
    <div className="min-h-screen bg-base">
      {/* Header */}
      <header className="border-b border-subtle bg-card/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto max-w-3xl px-4 py-3 flex items-center justify-between">
          <span className="font-semibold text-foreground tracking-tight">{report.brandName}</span>
          <span className="text-xs text-secondary-text">股票分析报告</span>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-3xl px-4 py-8 space-y-5">
        {/* Stock identity */}
        <div className="terminal-card rounded-2xl p-5 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-foreground">{report.stockName}</h1>
              <p className="text-sm text-secondary-text mt-0.5 font-mono">{report.stockCode}</p>
            </div>
            {report.sentimentScore !== null && (
              <div className="text-right">
                <span className={`text-3xl font-bold font-mono ${sentimentColor}`}>
                  {report.sentimentScore}
                </span>
                <p className="text-xs text-secondary-text mt-0.5">情绪指数 / 100</p>
              </div>
            )}
          </div>

          {/* Operation advice */}
          {report.operationAdvice && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-secondary-text uppercase tracking-wider">操作建议</span>
              <span className="rounded-full border border-cyan/30 bg-cyan/10 px-3 py-0.5 text-sm font-medium text-cyan">
                {report.operationAdvice}
              </span>
            </div>
          )}

          {/* Trend prediction */}
          {report.trendPrediction && (
            <div>
              <p className="text-xs text-secondary-text uppercase tracking-wider mb-1">趋势判断</p>
              <p className="text-sm text-foreground leading-relaxed">{report.trendPrediction}</p>
            </div>
          )}
        </div>

        {/* Analysis summary */}
        {report.analysisSummary && (
          <div className="terminal-card rounded-2xl p-5">
            <p className="text-xs text-secondary-text uppercase tracking-wider mb-3">综合分析</p>
            <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">
              {report.analysisSummary}
            </p>
          </div>
        )}

        {/* Strategy points */}
        {(report.idealBuy !== null || report.secondaryBuy !== null || report.stopLoss !== null || report.takeProfit !== null) && (
          <div className="terminal-card rounded-2xl p-5">
            <p className="text-xs text-secondary-text uppercase tracking-wider mb-3">策略点位</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {report.idealBuy !== null && (
                <div className="rounded-xl border border-[var(--home-panel-border)] bg-[var(--home-panel-subtle-bg)] p-3">
                  <p className="text-xs text-secondary-text mb-1">首选买入</p>
                  <p className="text-lg font-bold font-mono text-[var(--home-strategy-buy)]">
                    {report.idealBuy}
                  </p>
                </div>
              )}
              {report.secondaryBuy !== null && (
                <div className="rounded-xl border border-[var(--home-panel-border)] bg-[var(--home-panel-subtle-bg)] p-3">
                  <p className="text-xs text-secondary-text mb-1">次选买入</p>
                  <p className="text-lg font-bold font-mono text-[var(--home-strategy-secondary)]">
                    {report.secondaryBuy}
                  </p>
                </div>
              )}
              {report.stopLoss !== null && (
                <div className="rounded-xl border border-[var(--home-panel-border)] bg-[var(--home-panel-subtle-bg)] p-3">
                  <p className="text-xs text-secondary-text mb-1">止损</p>
                  <p className="text-lg font-bold font-mono text-[var(--home-strategy-stop)]">
                    {report.stopLoss}
                  </p>
                </div>
              )}
              {report.takeProfit !== null && (
                <div className="rounded-xl border border-[var(--home-panel-border)] bg-[var(--home-panel-subtle-bg)] p-3">
                  <p className="text-xs text-secondary-text mb-1">目标价</p>
                  <p className="text-lg font-bold font-mono text-[var(--home-strategy-take)]">
                    {report.takeProfit}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Analysis timestamp */}
        {report.analysisCreatedAt && (
          <p className="text-xs text-secondary-text px-1">
            分析时间：{new Date(report.analysisCreatedAt).toLocaleString('zh-CN')}
          </p>
        )}
      </main>

      {/* Footer CTA */}
      <footer className="border-t border-subtle mt-8 py-8">
        <div className="mx-auto max-w-3xl px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-secondary-text">
            由 <span className="font-medium text-foreground">{report.brandName}</span> 提供分析
          </p>
          <Link
            to="/register"
            className="inline-flex items-center gap-1.5 rounded-xl border border-cyan/30 bg-cyan/10 px-4 py-2 text-sm font-medium text-cyan hover:bg-cyan/18 transition-colors"
          >
            注册查看完整分析报告
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
        </div>
      </footer>
    </div>
  );
};

export default SharePage;
