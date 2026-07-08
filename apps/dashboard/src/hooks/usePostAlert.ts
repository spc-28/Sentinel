import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/endpoints';
import { queryKeys } from '@/lib/queryKeys';
import type { AlertWebhookBody } from '@/types/api';

export function usePostAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AlertWebhookBody) => api.postAlert(body),
    onSuccess: () => {
      // A new alert may open or grow a group — refresh lists immediately.
      void qc.invalidateQueries({ queryKey: queryKeys.groups() });
    },
  });
}
