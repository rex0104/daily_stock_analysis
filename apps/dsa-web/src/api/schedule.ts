import apiClient from './index';

export type ScheduleConfig = {
  enabled: boolean;
  time: string; // "HH:MM"
};

export const scheduleApi = {
  get: async (): Promise<ScheduleConfig> => {
    const { data } = await apiClient.get<ScheduleConfig>('/api/v1/schedule');
    return data;
  },
  update: async (config: ScheduleConfig): Promise<ScheduleConfig> => {
    const { data } = await apiClient.put<ScheduleConfig>('/api/v1/schedule', config);
    return data;
  },
  runNow: async () => {
    const { data } = await apiClient.post('/api/v1/schedule/run-now');
    return data;
  },
};
