import { useMemo, useState } from 'react';

import { PageHeading } from '@/components/layout/AppShell';
import { IncidentGroupRow } from '@/components/domain/IncidentGroupRow';
import { Card, CardBody } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Input, Select } from '@/components/ui/Input';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { useIncidentGroups } from '@/hooks/useIncidentGroups';
import { cn } from '@/lib/cn';
import { titleCase } from '@/lib/format';
import type { AlertSeverity } from '@/types/enums';
import { SEVERITIES } from '@/types/enums';

type SortKey = 'recent' | 'alerts';

export function IncidentGroupsPage() {
  const { data, isLoading, isError, error, refetch } = useIncidentGroups();
  const [text, setText] = useState('');
  const [status, setStatus] = useState<'all' | 'open' | 'closed'>('all');
  const [sort, setSort] = useState<SortKey>('recent');
  const [severities, setSeverities] = useState<Set<AlertSeverity>>(new Set());

  const toggleSeverity = (s: AlertSeverity) =>
    setSeverities((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });

  const filtered = useMemo(() => {
    let rows = data ?? [];
    if (text.trim()) {
      const q = text.toLowerCase();
      rows = rows.filter((g) => g.title.toLowerCase().includes(q));
    }
    if (status !== 'all') rows = rows.filter((g) => g.status === status);
    if (severities.size > 0) rows = rows.filter((g) => severities.has(g.severity));
    rows = [...rows].sort((a, b) =>
      sort === 'alerts'
        ? b.alert_count - a.alert_count
        : new Date(b.last_activity_at).getTime() - new Date(a.last_activity_at).getTime(),
    );
    return rows;
  }, [data, text, status, severities, sort]);

  return (
    <div>
      <PageHeading
        title="Incident Groups"
        description="Correlated alerts. Each new group opens an AI investigation."
      />

      <Card>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder="Filter by title…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="max-w-xs"
            />
            <Select
              value={status}
              onChange={(e) => setStatus(e.target.value as typeof status)}
              className="w-32"
            >
              <option value="all">All status</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </Select>
            <Select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="w-40"
            >
              <option value="recent">Most recent</option>
              <option value="alerts">Most alerts</option>
            </Select>
            <div className="flex flex-wrap gap-1.5">
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => toggleSeverity(s)}
                  className={cn(
                    'rounded-md border px-2 py-1 text-xs font-medium transition-colors',
                    severities.has(s)
                      ? 'border-accent bg-accent/10 text-fg'
                      : 'border-border text-muted hover:text-fg',
                  )}
                >
                  {titleCase(s)}
                </button>
              ))}
            </div>
          </div>

          {isLoading ? (
            <SkeletonRows rows={6} />
          ) : isError ? (
            <ErrorState error={error} onRetry={() => void refetch()} />
          ) : filtered.length > 0 ? (
            <div className="space-y-2">
              {filtered.map((group) => (
                <IncidentGroupRow key={group.id} group={group} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No matching groups"
              message={
                (data?.length ?? 0) === 0
                  ? 'No incident groups exist yet.'
                  : 'Try clearing the filters above.'
              }
            />
          )}
        </CardBody>
      </Card>

      {(data?.length ?? 0) > 0 ? (
        <p className="mt-3 text-xs text-muted">
          Showing {filtered.length} of {data?.length} recent group
          {(data?.length ?? 0) === 1 ? '' : 's'} (API returns the 50 newest).
        </p>
      ) : null}
    </div>
  );
}
