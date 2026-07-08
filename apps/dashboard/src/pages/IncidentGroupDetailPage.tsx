import { ArrowLeft, ArrowRight, Layers } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { PageHeading } from '@/components/layout/AppShell';
import { AlertRow } from '@/components/domain/AlertRow';
import { SeverityBadge } from '@/components/domain/SeverityBadge';
import { StatusBadge } from '@/components/domain/StatusBadge';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { useIncidentGroup } from '@/hooks/useIncidentGroups';
import { useInvestigationByAlert } from '@/hooks/useInvestigation';
import { formatDateTime, relativeTime, shortId } from '@/lib/format';

function InvestigationLink({ leaderAlertId }: { leaderAlertId: string | null }) {
  const { data, isLoading } = useInvestigationByAlert(leaderAlertId);
  if (!leaderAlertId) return null;
  if (isLoading && data === undefined) {
    return <span className="text-sm text-muted">Resolving investigation…</span>;
  }
  if (!data) {
    return <span className="text-sm text-muted">Investigation pending…</span>;
  }
  return (
    <Link
      to={`/investigations/${data.investigation.id}`}
      className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:opacity-90"
    >
      View investigation
      <ArrowRight className="h-4 w-4" />
    </Link>
  );
}

export function IncidentGroupDetailPage() {
  const { id = '' } = useParams();
  const { data, isLoading, isError, error, refetch } = useIncidentGroup(id);

  return (
    <div>
      <Link
        to="/groups"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to groups
      </Link>

      {isLoading ? (
        <SkeletonRows rows={5} />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data ? (
        <>
          <PageHeading
            title={data.group.title}
            action={<InvestigationLink leaderAlertId={data.group.leader_alert_id} />}
          />
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <SeverityBadge severity={data.group.severity} />
            <StatusBadge status={data.group.status} />
            <span className="inline-flex items-center gap-1 text-xs text-muted">
              <Layers className="h-3.5 w-3.5" />
              {data.alerts.length} correlated alert{data.alerts.length === 1 ? '' : 's'}
            </span>
            {data.group.service_id ? (
              <span className="font-mono text-xs text-muted">
                service {shortId(data.group.service_id)}
              </span>
            ) : null}
            <span className="text-xs text-muted">
              last activity {relativeTime(data.group.last_activity_at)} ·{' '}
              {formatDateTime(data.group.last_activity_at)}
            </span>
          </div>

          <Card>
            <CardHeader
              title="Correlated alerts"
              subtitle="Alerts folded into this group; the leader drives severity and the investigation"
            />
            <CardBody className="space-y-2">
              {data.alerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  isLeader={alert.id === data.group.leader_alert_id}
                />
              ))}
            </CardBody>
          </Card>
        </>
      ) : null}
    </div>
  );
}
