import { AlertCircle, Check, Loader2 } from 'lucide-react';

import { cn } from '@/lib/cn';
import type { InvestigationStatus } from '@/types/enums';

type StepState = 'done' | 'active' | 'pending' | 'error';

const STEPS = ['Queued', 'Investigating', 'Report ready'] as const;

function statesFor(status: InvestigationStatus): StepState[] {
  switch (status) {
    case 'pending':
      return ['active', 'pending', 'pending'];
    case 'running':
      return ['done', 'active', 'pending'];
    case 'completed':
      return ['done', 'done', 'done'];
    case 'failed':
      return ['done', 'error', 'pending'];
  }
}

function Node({ state, index }: { state: StepState; index: number }) {
  const circle =
    state === 'done'
      ? 'border-emerald-500 bg-emerald-500 text-white'
      : state === 'active'
        ? 'border-sky-500 bg-sky-500 text-white'
        : state === 'error'
          ? 'border-red-500 bg-red-500 text-white'
          : 'border-border bg-surface text-muted';
  return (
    <div className={cn('flex h-7 w-7 items-center justify-center rounded-full border', circle)}>
      {state === 'done' ? (
        <Check className="h-4 w-4" />
      ) : state === 'active' ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : state === 'error' ? (
        <AlertCircle className="h-4 w-4" />
      ) : (
        <span className="text-xs">{index + 1}</span>
      )}
    </div>
  );
}

export function InvestigationStepper({ status }: { status: InvestigationStatus }) {
  const states = statesFor(status);
  return (
    <div className="flex items-center">
      {STEPS.map((label, i) => {
        const state = states[i] ?? 'pending';
        const connectorDone = states[i + 1] && states[i + 1] !== 'pending';
        return (
          <div key={label} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-1.5">
              <Node state={state} index={i} />
              <span
                className={cn(
                  'text-[11px] font-medium',
                  state === 'pending' ? 'text-muted' : 'text-fg',
                )}
              >
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 ? (
              <div
                className={cn(
                  'mx-2 h-0.5 flex-1 rounded-full',
                  connectorDone ? 'bg-emerald-500' : 'bg-border',
                )}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
