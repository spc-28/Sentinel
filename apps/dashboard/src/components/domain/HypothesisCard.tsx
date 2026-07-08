import { cn } from '@/lib/cn';
import { ProgressBar } from '@/components/ui/ProgressBar';
import type { HypothesisRead } from '@/types/api';

export function HypothesisCard({ hypothesis }: { hypothesis: HypothesisRead }) {
  const pct = Math.round(hypothesis.confidence * 100);
  const leading = hypothesis.rank === 1;
  return (
    <div
      className={cn(
        'rounded-lg border bg-surface p-4',
        leading ? 'border-accent/40 ring-1 ring-accent/20' : 'border-border',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'flex h-5 w-5 items-center justify-center rounded text-[11px] font-semibold',
              leading ? 'bg-accent text-accent-fg' : 'bg-surface-2 text-muted',
            )}
          >
            {hypothesis.rank}
          </span>
          <span className="text-sm font-medium text-fg">{hypothesis.statement}</span>
        </div>
        <span className="shrink-0 text-xs font-medium tabular-nums text-muted">{pct}%</span>
      </div>
      {hypothesis.description ? (
        <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-muted">
          {hypothesis.description}
        </p>
      ) : null}
      <ProgressBar value={hypothesis.confidence} className="mt-3" />
    </div>
  );
}
