import apiClient from './index';
import { toCamelCase } from './utils';

export type OnboardingStatus = {
  completed: boolean;
  steps: {
    llmConfigured: boolean;
    stocksAdded: boolean;
    firstAnalysisDone: boolean;
  };
};

export const onboardingApi = {
  getStatus: async (): Promise<OnboardingStatus> => {
    const { data } = await apiClient.get('/api/v1/onboarding/status');
    return toCamelCase<OnboardingStatus>(data);
  },
  complete: () => apiClient.post('/api/v1/onboarding/complete'),
};
