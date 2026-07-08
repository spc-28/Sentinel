import { AlertTriangle, ArrowLeft, FlaskConical, Loader2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';

import { ConfirmCausePanel } from '@/components/domain/ConfirmCausePanel';
import { CostTokenChips } from '@/components/domain/CostTokenChips';
import { HypothesisCard } from '@/components/domain/HypothesisCard';
import { InvestigationStepper } from '@/components/domain/InvestigationStepper';
import { RcaReport } from '@/components/domain/RcaReport';
import { StatusBadge } from '@/components/domain/StatusBadge';
import { SuggestFixPanel } from '@/components/domain/SuggestFixPanel';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton, SkeletonRows } from '@/components/ui/Skeleton';
import { useInvestigation } from '@/hooks/useInvestigation';
import { formatDuration, relativeTime, shortId } from '@/lib/format';

export function InvestigationDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useInvestigation(id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <SkeletonRows rows={4} />
      </div>
    );
  }
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;
  if (!data) return null;

  const { investigation, hypotheses, report } = data;
  const active = investigation.status === 'pending' || investigation.status === 'running';
  const ranked = [...hypotheses].sort((a, b) => a.rank - b.rank);

  return (
    <div>
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </button>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-fg">Investigation</h1>
          <StatusBadge status={investigation.status} />
          <span className="font-mono text-xs text-muted">{shortId(investigation.id)}</span>
        </div>
        <CostTokenChips investigation={investigation} />
      </div>

      {/* Lifecycle */}
      <Card>
        <CardBody className="space-y-4">
          <InvestigationStepper status={investigation.status} />
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted">
            <span>Started {relativeTime(investigation.started_at)}</span>
            <span>
              {investigation.completed_at
                ? `Took ${formatDuration(investigation.started_at, investigation.completed_at)}`
                : active
                  ? `Running for ${formatDuration(investigation.started_at, null)}`
                  : '—'}
            </span>
          </div>
          {investigation.status === 'failed' && investigation.error ? (
            <div className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/5 p-3 text-sm text-fg">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
              <span className="whitespace-pre-wrap">{investigation.error}</span>
            </div>
          ) : null}
        </CardBody>
      </Card>

      {/* Hypotheses */}
      <Card className="mt-4">
        <CardHeader title="Hypotheses" subtitle="Ranked candidate causes with confidence" />
        <CardBody>
          {ranked.length > 0 ? (
            <div className="space-y-3">
              {ranked.map((h) => (
                <HypothesisCard key={h.id} hypothesis={h} />
              ))}
            </div>
          ) : active ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              Gathering evidence and forming hypotheses…
            </div>
          ) : (
            <p className="text-sm text-muted">No hypotheses were recorded.</p>
          )}
        </CardBody>
      </Card>

      {/* Report */}
      <Card className="mt-4">
        <CardHeader title="Root-cause report" subtitle="Findings, timeline, and recommended fix" />
        <CardBody>
          {report ? (
            <RcaReport report={report} />
          ) : active ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              The report will appear here once the investigation completes.
            </div>
          ) : (
            <EmptyState
              icon={<FlaskConical className="h-6 w-6" />}
              title="No report"
              message="This investigation finished without a root-cause report (e.g. a false alarm)."
            />
          )}
        </CardBody>
      </Card>

      {/* Actions */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Suggested fix" subtitle="From the report, plus a draft revert PR" />
          <CardBody>
            <SuggestFixPanel investigationId={investigation.id} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Confirm cause" subtitle="Human feedback that trains Sentinel's memory" />
          <CardBody>
            <ConfirmCausePanel investigationId={investigation.id} />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
