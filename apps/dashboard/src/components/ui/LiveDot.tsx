import { cn } from '@/lib/cn';

// A small pulsing dot signalling live/active polling.
export function LiveDot({ active = true, className }: { active?: boolean; className?: string }) {
  return (
    <span className={cn('relative inline-flex h-2 w-2', className)}>
      {active ? (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
      ) : null}
      <span
        className={cn(
          'relative inline-flex h-2 w-2 rounded-full',
          active ? 'bg-emerald-500' : 'bg-zinc-400',
        )}
      />
    </span>
  );
}
