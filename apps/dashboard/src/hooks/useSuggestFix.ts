import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';

// Lazy: only fetched once the user clicks "Suggest fix".
export function useSuggestFix(id: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.suggestFix(id),
    queryFn: () => api.getSuggestFix(id),
    enabled,
    staleTime: 60_000,
  });
}
