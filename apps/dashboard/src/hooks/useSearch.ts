import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';

export function useSearch(q: string) {
  return useQuery({
    queryKey: queryKeys.search(q),
    queryFn: () => api.searchInvestigations(q),
    enabled: q.trim().length > 0,
    staleTime: 30_000,
  });
}
