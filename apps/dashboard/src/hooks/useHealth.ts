import { useQuery } from '@tanstack/react-query';

import { config } from '@/config';
import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';

// Backs the header status dot. Polls slowly and never spams retries.
export function useReady() {
  return useQuery({
    queryKey: queryKeys.ready(),
    queryFn: api.getReady,
    refetchInterval: config.pollStatsMs,
    retry: false,
  });
}
