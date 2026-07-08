import { useQuery } from '@tanstack/react-query';

import { config } from '@/config';
import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';
import type { InvestigationDetail } from '@/types/api';

// Poll fast only while the investigation is still in flight; stop once terminal.
function activeInterval(data: InvestigationDetail | null | undefined): number | false {
  const status = data?.investigation.status;
  return status === 'pending' || status === 'running' ? config.pollActiveMs : false;
}

export function useInvestigation(id: string) {
  return useQuery({
    queryKey: queryKeys.investigation(id),
    queryFn: () => api.getInvestigation(id),
    refetchInterval: (query) => activeInterval(query.state.data),
  });
}

// Resolves an investigation from an alert id; null until the worker opens it.
export function useInvestigationByAlert(alertId: string | null | undefined, enabled = true) {
  return useQuery({
    queryKey: queryKeys.investigationByAlert(alertId ?? ''),
    queryFn: () => api.getInvestigationByAlert(alertId as string),
    enabled: Boolean(alertId) && enabled,
    refetchInterval: (query) => {
      // Keep polling while it doesn't exist yet or is still running.
      const data = query.state.data;
      if (data == null) return config.pollActiveMs;
      return activeInterval(data);
    },
  });
}
