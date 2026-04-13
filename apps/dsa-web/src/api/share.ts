import apiClient from './index';
import { toCamelCase } from './utils';

export type ShareResult = {
  shareToken: string;
  analysisHistoryId: number;
  brandName: string;
  createdAt: string;
};

export type SharedReport = ShareResult & {
  stockCode: string;
  stockName: string;
  reportType: string;
  sentimentScore: number | null;
  operationAdvice: string;
  trendPrediction: string;
  analysisSummary: string;
  idealBuy: number | null;
  secondaryBuy: number | null;
  stopLoss: number | null;
  takeProfit: number | null;
  analysisCreatedAt: string;
};

export const shareApi = {
  create: async (analysisHistoryId: number, brandName?: string): Promise<ShareResult> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/share', {
      analysis_history_id: analysisHistoryId,
      brand_name: brandName,
    });
    return toCamelCase<ShareResult>(response.data);
  },

  get: async (token: string): Promise<SharedReport> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/share/${token}`);
    return toCamelCase<SharedReport>(response.data);
  },

  list: async (): Promise<ShareResult[]> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/share');
    const data = toCamelCase<{ items: ShareResult[] }>(response.data);
    return data.items;
  },

  revoke: async (token: string): Promise<unknown> => {
    const response = await apiClient.delete(`/api/v1/share/${token}`);
    return response.data;
  },
};
