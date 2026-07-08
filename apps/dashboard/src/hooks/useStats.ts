import { useQuery } from '@tanstack/react-query';

import { config } from '@/config';
import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats(),
    queryFn: api.getStats,
    refetchInterval: config.pollStatsMs,
  });
}
