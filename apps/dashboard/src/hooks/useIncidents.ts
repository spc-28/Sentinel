import { useQuery } from '@tanstack/react-query';

import { config } from '@/config';
import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';

export function useIncidents(params: { service?: string; lastNHours?: number } = {}) {
  return useQuery({
    queryKey: queryKeys.incidents(params),
    queryFn: () => api.listIncidents(params),
    refetchInterval: config.pollListMs,
  });
}
