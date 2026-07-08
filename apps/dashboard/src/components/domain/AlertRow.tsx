import { ChevronDown, ChevronRight, Crown } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import { formatDateTime } from '@/lib/format';
import type { AlertRead } from '@/types/api';
import { SeverityBadge } from './SeverityBadge';
import { StatusBadge } from './StatusBadge';

export function AlertRow({ alert, isLeader }: { alert: AlertRead; isLeader: boolean }) {
  const [open, setOpen] = useState(false);
  const hasPayload = alert.payload && Object.keys(alert.payload).length > 0;

  return (
    <div
      className={cn(
        'rounded-lg border bg-surface',
        isLeader ? 'border-accent/40 ring-1 ring-accent/20' : 'border-border',
      )}
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <SeverityBadge severity={alert.severity} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-fg">{alert.title}</p>
            {isLeader ? (
              <span title="Leader alert" className="text-accent">
                <Crown className="h-3.5 w-3.5" />
              </span>
            ) : null}
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
            {alert.source ? <Badge className="bg-surface-2 ring-border">{alert.source}</Badge> : null}
            <span>{formatDateTime(alert.triggered_at)}</span>
            {alert.fingerprint ? <span className="font-mono">{alert.fingerprint}</span> : null}
          </div>
        </div>
        <StatusBadge status={alert.status} />
        {hasPayload ? (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? 'Hide payload' : 'Show payload'}
            className="text-muted transition-colors hover:text-fg"
          >
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        ) : null}
      </div>
      {open && hasPayload ? (
        <pre className="overflow-x-auto border-t border-border bg-surface-2 px-4 py-3 font-mono text-[11px] leading-relaxed text-muted">
          {JSON.stringify(alert.payload, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
