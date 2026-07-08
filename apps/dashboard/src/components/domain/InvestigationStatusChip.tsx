import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/Badge';
import { useInvestigationByAlert } from '@/hooks/useInvestigation';
import { statusStyle } from '@/lib/severity';
import { StatusBadge } from './StatusBadge';

// Resolves and shows the investigation status for a group's leader alert.
// Bounded use only (top N rows) to keep the request fan-out small.
export function InvestigationStatusChip({ leaderAlertId }: { leaderAlertId: string | null }) {
  const { data, isLoading } = useInvestigationByAlert(leaderAlertId);
  if (!leaderAlertId) return null;
  if (isLoading && data === undefined) {
    return <span className="text-xs text-muted">…</span>;
  }
  if (!data) {
    return <Badge className={statusStyle('pending')}>Queued</Badge>;
  }
  return (
    <Link
      to={`/investigations/${data.investigation.id}`}
      onClick={(e) => e.stopPropagation()}
      className="transition-opacity hover:opacity-80"
    >
      <StatusBadge status={data.investigation.status} />
    </Link>
  );
}
