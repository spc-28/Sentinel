import { Coins, ArrowDownToLine, ArrowUpFromLine } from 'lucide-react';
import type { ReactNode } from 'react';

import { formatCurrency, formatTokens } from '@/lib/format';
import type { InvestigationRead } from '@/types/api';

function Chip({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-surface-2 px-3 py-1.5">
      <span className="text-muted">{icon}</span>
      <span className="text-xs text-muted">{label}</span>
      <span className="text-sm font-medium tabular-nums text-fg">{value}</span>
    </div>
  );
}

export function CostTokenChips({ investigation }: { investigation: InvestigationRead }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Chip
        icon={<Coins className="h-3.5 w-3.5" />}
        label="Cost"
        value={formatCurrency(investigation.cost_usd)}
      />
      <Chip
        icon={<ArrowDownToLine className="h-3.5 w-3.5" />}
        label="Input"
        value={formatTokens(investigation.input_tokens)}
      />
      <Chip
        icon={<ArrowUpFromLine className="h-3.5 w-3.5" />}
        label="Output"
        value={formatTokens(investigation.output_tokens)}
      />
    </div>
  );
}
