import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';
import { Skeleton } from './Skeleton';

export function StatCard({
  label,
  value,
  icon,
  hint,
  loading,
  className,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  hint?: string;
  loading?: boolean;
  className?: string;
}) {
  return (
    <div className={cn('rounded-lg border border-border bg-surface p-4 shadow-subtle', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted">{label}</span>
        {icon ? <span className="text-muted">{icon}</span> : null}
      </div>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-24" />
      ) : (
        <div className="mt-1 text-2xl font-semibold tabular-nums text-fg">{value}</div>
      )}
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}
