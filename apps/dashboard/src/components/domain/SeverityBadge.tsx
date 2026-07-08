import { Badge } from '@/components/ui/Badge';
import { titleCase } from '@/lib/format';
import { severityBadge, severityDot } from '@/lib/severity';
import type { AlertSeverity } from '@/types/enums';

export function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  return (
    <Badge
      className={severityBadge[severity]}
      dot={<span className={`h-1.5 w-1.5 rounded-full ${severityDot[severity]}`} />}
    >
      {titleCase(severity)}
    </Badge>
  );
}
