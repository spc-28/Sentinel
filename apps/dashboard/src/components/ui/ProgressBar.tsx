import { cn } from '@/lib/cn';

// A 0..1 value rendered as a subtle bar. Color shifts with confidence.
export function ProgressBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  const tone =
    value >= 0.66
      ? 'bg-emerald-500'
      : value >= 0.33
        ? 'bg-amber-500'
        : 'bg-zinc-400';
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-surface-2', className)}>
      <div className={cn('h-full rounded-full transition-all', tone)} style={{ width: `${pct}%` }} />
    </div>
  );
}
