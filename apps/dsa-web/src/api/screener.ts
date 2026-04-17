import apiClient from './index';

export interface Strategy {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface ScreenerCandidate {
  code: string;
  name: string;
  price: number;
  changePct: number;
  volumeRatio: number;
  pct5d: number;
  summary?: string;
}

export const screenerApi = {
  /** Fetch available strategies. */
  listStrategies: async (): Promise<Strategy[]> => {
    const res = await apiClient.get<Strategy[]>('/api/v1/screener/strategies');
    return res.data;
  },

  /**
   * Start a screening scan via SSE.
   * Returns a cleanup function. Call onEvent for each SSE event.
   */
  scan: (
    strategy: string,
    onEvent: (type: string, data: Record<string, unknown>) => void,
    onError: (err: Event) => void,
  ): (() => void) => {
    const baseUrl = apiClient.defaults.baseURL || '';
    const url = `${baseUrl}/api/v1/screener/scan`;

    // Use fetch + ReadableStream for POST SSE (EventSource only supports GET)
    const controller = new AbortController();

    (async () => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ strategy }),
          credentials: 'include',
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          onError(new Event('fetch-error'));
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = '';
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ') && currentEvent) {
              try {
                const data = JSON.parse(line.slice(6));
                onEvent(currentEvent, data);
              } catch { /* skip malformed */ }
              currentEvent = '';
            }
          }
        }
      } catch (err) {
        if ((err as DOMException)?.name !== 'AbortError') {
          onError(new Event('stream-error'));
        }
      }
    })();

    return () => controller.abort();
  },
};
