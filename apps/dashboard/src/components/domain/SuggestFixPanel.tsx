import { ExternalLink, Lightbulb, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { useSuggestFix } from '@/hooks/useSuggestFix';

export function SuggestFixPanel({ investigationId }: { investigationId: string }) {
  const [enabled, setEnabled] = useState(false);
  const { data, isLoading, isError, error, refetch } = useSuggestFix(investigationId, enabled);

  if (!enabled) {
    return (
      <Button variant="subtle" onClick={() => setEnabled(true)}>
        <Lightbulb className="h-4 w-4" />
        Suggest a fix
      </Button>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Drafting a fix and revert PR…
      </div>
    );
  }

  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;
  if (!data) return null;

  return (
    <div className="space-y-3 rounded-lg border border-border bg-surface-2 p-4">
      {data.root_cause ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Root cause</p>
          <p className="mt-1 text-sm text-fg">{data.root_cause}</p>
        </div>
      ) : null}
      {data.recommended_fix ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Recommended fix</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-fg">{data.recommended_fix}</p>
        </div>
      ) : null}
      {data.revert_pr_url ? (
        <a
          href={data.revert_pr_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
        >
          {data.revert_title ?? 'Draft revert PR'}
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      ) : null}
      <p className="text-xs text-muted">{data.note}</p>
    </div>
  );
}
