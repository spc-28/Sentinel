import { Layers } from 'lucide-react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { relativeTime, shortId } from '@/lib/format';
import type { IncidentGroupRead } from '@/types/api';
import { SeverityBadge } from './SeverityBadge';
import { StatusBadge } from './StatusBadge';

export function IncidentGroupRow({
  group,
  trailing,
}: {
  group: IncidentGroupRead;
  trailing?: ReactNode;
}) {
  const navigate = useNavigate();
  const go = () => navigate(`/groups/${group.id}`);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={go}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          go();
        }
      }}
      className="flex cursor-pointer items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3 transition-colors hover:bg-surface-2"
    >
      <SeverityBadge severity={group.severity} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-fg">{group.title}</p>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted">
          {group.service_id ? (
            <span className="inline-flex items-center gap-1 font-mono">
              <Layers className="h-3 w-3" />
              {shortId(group.service_id)}
            </span>
          ) : null}
          <span>
            {group.alert_count} alert{group.alert_count === 1 ? '' : 's'}
          </span>
          <span>·</span>
          <span>{relativeTime(group.last_activity_at)}</span>
        </div>
      </div>
      <StatusBadge status={group.status} />
      {trailing}
    </div>
  );
}
