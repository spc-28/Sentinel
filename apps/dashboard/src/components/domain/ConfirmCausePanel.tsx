import { CheckCircle2, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
import { useConfirmCause } from '@/hooks/useConfirmCause';
import { ApiError } from '@/lib/apiClient';

export function ConfirmCausePanel({ investigationId }: { investigationId: string }) {
  const [cause, setCause] = useState('');
  const mutation = useConfirmCause(investigationId);

  if (mutation.isSuccess) {
    const incident = mutation.data;
    return (
      <div className="space-y-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-fg">
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          Recorded to memory
        </div>
        <p className="text-sm text-muted">{incident.confirmed_cause ?? incident.root_cause}</p>
        <div className="flex flex-wrap gap-2 pt-1">
          <Badge className="bg-surface-2 ring-border">
            weight {incident.weight.toFixed(2)}
          </Badge>
          <Badge className="bg-surface-2 ring-border">
            {incident.occurrences} occurrence{incident.occurrences === 1 ? '' : 's'}
          </Badge>
          {incident.match_score != null ? (
            <Badge className="bg-surface-2 ring-border">
              match {incident.match_score.toFixed(2)}
            </Badge>
          ) : null}
          {incident.is_pattern ? (
            <Badge className="bg-accent/10 text-fg ring-accent/30">
              pattern{incident.pattern_label ? `: ${incident.pattern_label}` : ''}
            </Badge>
          ) : null}
        </div>
      </div>
    );
  }

  const notFound = mutation.error instanceof ApiError && mutation.error.status === 404;

  return (
    <div className="space-y-2">
      <Textarea
        rows={3}
        placeholder="Confirm the real root cause… (re-weights Sentinel's memory)"
        value={cause}
        onChange={(e) => setCause(e.target.value)}
      />
      <div className="flex items-center gap-3">
        <Button
          onClick={() => mutation.mutate(cause.trim())}
          disabled={cause.trim().length === 0 || mutation.isPending}
        >
          {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Confirm cause
        </Button>
        {mutation.isError ? (
          <span className="text-xs text-red-500">
            {notFound
              ? 'No remembered incident for this investigation yet.'
              : 'Could not record — try again.'}
          </span>
        ) : null}
      </div>
    </div>
  );
}
