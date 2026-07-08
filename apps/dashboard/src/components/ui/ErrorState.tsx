import { AlertTriangle } from 'lucide-react';

import { ApiError } from '@/lib/apiClient';
import { Button } from './Button';

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof Error) return error.message;
  return 'Something went wrong.';
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border px-6 py-12 text-center">
      <AlertTriangle className="h-6 w-6 text-red-500" />
      <div>
        <p className="text-sm font-medium text-fg">Couldn’t load this</p>
        <p className="mt-1 max-w-md text-xs text-muted">{messageFor(error)}</p>
      </div>
      {onRetry ? (
        <Button variant="subtle" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}
