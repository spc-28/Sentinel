import { Badge } from '@/components/ui/Badge';
import { titleCase } from '@/lib/format';
import { statusStyle } from '@/lib/severity';

// One badge for any status value (investigation / group / incident / alert).
// The `running` status gets a subtle pulsing dot.
export function StatusBadge({ status }: { status: string }) {
  const pulsing = status === 'running';
  return (
    <Badge
      className={statusStyle(status)}
      dot={
        pulsing ? (
          <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-sky-500" />
        ) : undefined
      }
    >
      {titleCase(status)}
    </Badge>
  );
}
