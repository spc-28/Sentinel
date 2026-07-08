import { useQueries } from '@tanstack/react-query';

import { config } from '@/config';
import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';
import type { IncidentGroupRead, InvestigationDetail } from '@/types/api';

// Hydrates investigations for the top `limit` groups (via their leader alert),
// bounding the by-alert fan-out. Used by the cost view to chart per-run spend.
export function useInvestigationsForGroups(groups: IncidentGroupRead[], limit: number) {
  const targets = groups.slice(0, limit).filter((g) => g.leader_alert_id);
  const results = useQueries({
    queries: targets.map((g) => ({
      queryKey: queryKeys.investigationByAlert(g.leader_alert_id as string),
      queryFn: () => api.getInvestigationByAlert(g.leader_alert_id as string),
      staleTime: config.pollListMs,
    })),
  });
  const investigations = results
    .map((r) => r.data)
    .filter((d): d is InvestigationDetail => Boolean(d));
  return { investigations, isLoading: results.some((r) => r.isLoading) };
}
