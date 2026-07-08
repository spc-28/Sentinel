import { useQuery } from '@tanstack/react-query';

import { config } from '@/config';
import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';

export function useIncidentGroups() {
  return useQuery({
    queryKey: queryKeys.groups(),
    queryFn: api.listIncidentGroups,
    refetchInterval: config.pollListMs,
  });
}

export function useIncidentGroup(id: string) {
  return useQuery({
    queryKey: queryKeys.group(id),
    queryFn: () => api.getIncidentGroup(id),
    refetchInterval: config.pollListMs,
  });
}
