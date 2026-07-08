import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';

export function useConfirmCause(investigationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cause: string) => api.confirmCause(investigationId, cause),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.investigation(investigationId) });
    },
  });
}
