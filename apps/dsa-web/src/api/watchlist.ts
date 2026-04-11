import apiClient from './index';
import { toCamelCase } from './utils';

export type WatchlistItem = {
  stockCode: string;
  stockName: string | null;
  createdAt: string;
};

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
};
