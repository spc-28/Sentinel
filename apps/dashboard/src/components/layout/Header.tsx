import { useIsFetching } from '@tanstack/react-query';

import { LiveDot } from '@/components/ui/LiveDot';
import { useReady } from '@/hooks/useHealth';
import { cn } from '@/lib/cn';
import { ThemeToggle } from './ThemeToggle';

export function Header() {
  const { data, isError } = useReady();
  const fetching = useIsFetching() > 0;

  const healthy = !isError && data?.status === 'ready';
  const label = isError ? 'API offline' : healthy ? 'API healthy' : 'API degraded';

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <div className="flex items-center gap-2 text-sm">
        <LiveDot active={fetching} />
        <span className="text-muted">{fetching ? 'Live — syncing…' : 'Live'}</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              isError ? 'bg-red-500' : healthy ? 'bg-emerald-500' : 'bg-amber-500',
            )}
          />
          <span className="text-muted">{label}</span>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
