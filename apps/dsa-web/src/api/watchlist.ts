import apiClient from './index';
import { toCamelCase } from './utils';

// ============ Basic types ============

export type WatchlistItem = {
  stockCode: string;
  stockName: string | null;
  createdAt: string;
};

// ============ Enriched types ============

export type WatchlistPrice = {
  close: number;
  pctChg: number;
};

export type WatchlistAnalysis = {
  sentimentScore: number;
  operationAdvice: string;
  analysisSummary: string;
  analyzedAt: string;
};

export type WatchlistPosition = {
  quantity: number;
  avgCost: number;
  marketValue: number;
  unrealizedPnl: number;
  pnlPct: number;
};

export type WatchlistTimelineEntry = {
  date: string;
  sentimentScore: number;
  operationAdvice: string;
};

export type EnrichedWatchlistItem = {
  stockCode: string;
  stockName: string;
  groupId: string;
  sortOrder: number;
  market: string;
  price: WatchlistPrice | null;
  analysis: WatchlistAnalysis | null;
  position: WatchlistPosition | null;
  sparkline: number[];
  historyTimeline: WatchlistTimelineEntry[];
};

export type WatchlistGroup = {
  groupId: string;
  groupName: string;
  sortOrder: number;
  items: EnrichedWatchlistItem[];
};

export type EnrichedWatchlistResponse = {
  groups: WatchlistGroup[];
};

// ============ API ============

export const watchlistApi = {
  list: async (): Promise<WatchlistItem[]> => {
    const response = await apiClient.get<{ items: unknown[] }>('/api/v1/watchlist');
    return (response.data.items || []).map((item) => toCamelCase<WatchlistItem>(item));
  },

  add: async (stockCode: string, stockName?: string): Promise<WatchlistItem> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/watchlist', {
      stock_code: stockCode,
      ...(stockName !== undefined && { stock_name: stockName }),
    });
    return toCamelCase<WatchlistItem>(response.data);
  },

  remove: async (stockCode: string): Promise<void> => {
    await apiClient.delete(`/api/v1/watchlist/${stockCode}`);
  },

  getEnriched: async (): Promise<EnrichedWatchlistResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/watchlist/enriched');
    return toCamelCase<EnrichedWatchlistResponse>(response.data);
  },

  reorder: async (items: { stockCode: string; sortOrder: number; groupId: string }[]): Promise<void> => {
    await apiClient.put('/api/v1/watchlist/reorder', {
      items: items.map((i) => ({
        stock_code: i.stockCode,
        sort_order: i.sortOrder,
        group_id: i.groupId,
      })),
    });
  },

  createGroup: async (name: string): Promise<void> => {
    await apiClient.post('/api/v1/watchlist/groups', { name });
  },

  renameGroup: async (groupId: string, name: string): Promise<void> => {
    await apiClient.put(`/api/v1/watchlist/groups/${groupId}`, { name });
  },

  deleteGroup: async (groupId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/watchlist/groups/${groupId}`);
  },
};
