import { IncidentGroupRow } from './IncidentGroupRow';
import { InvestigationStatusChip } from './InvestigationStatusChip';
import type { IncidentGroupRead } from '@/types/api';

// Only the top `hydrate` rows resolve their investigation status, to bound the
// by-alert request fan-out.
export function LiveFeed({
  groups,
  hydrate = 8,
}: {
  groups: IncidentGroupRead[];
  hydrate?: number;
}) {
  return (
    <div className="space-y-2">
      {groups.map((group, i) => (
        <IncidentGroupRow
          key={group.id}
          group={group}
          trailing={
            i < hydrate ? <InvestigationStatusChip leaderAlertId={group.leader_alert_id} /> : null
          }
        />
      ))}
    </div>
  );
}
