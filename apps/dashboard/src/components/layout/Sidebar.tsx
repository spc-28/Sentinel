import { Activity, DollarSign, LayoutGrid, Play, ShieldCheck } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { cn } from '@/lib/cn';

const nav = [
  { to: '/', label: 'Overview', icon: Activity, end: true },
  { to: '/groups', label: 'Incident Groups', icon: LayoutGrid, end: false },
  { to: '/cost', label: 'AI Cost', icon: DollarSign, end: false },
  { to: '/demo', label: 'Demo Console', icon: Play, end: false },
];

export function Sidebar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex h-14 items-center gap-2 border-b border-border px-5">
        <ShieldCheck className="h-5 w-5 text-accent" />
        <span className="text-sm font-semibold text-fg">Sentinel</span>
        <span className="ml-1 rounded bg-surface-2 px-1.5 py-0.5 text-[10px] font-medium text-muted">
          SRE
        </span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-surface-2 text-fg'
                  : 'text-muted hover:bg-surface-2 hover:text-fg',
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border p-4 text-[11px] leading-relaxed text-muted">
        AI SRE platform — live investigation demo.
      </div>
    </aside>
  );
}
