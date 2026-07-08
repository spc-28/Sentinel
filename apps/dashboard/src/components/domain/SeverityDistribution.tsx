import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

import { titleCase } from '@/lib/format';
import { severityColor } from '@/lib/severity';
import type { IncidentGroupRead } from '@/types/api';
import { SEVERITIES } from '@/types/enums';

export function SeverityDistribution({ groups }: { groups: IncidentGroupRead[] }) {
  const counts = SEVERITIES.map((s) => ({
    severity: s,
    name: titleCase(s),
    value: groups.filter((g) => g.severity === s).length,
  })).filter((d) => d.value > 0);

  if (groups.length === 0) {
    return <p className="text-xs text-muted">No groups yet.</p>;
  }

  return (
    <div className="flex items-center gap-6">
      <div className="h-36 w-36 shrink-0">
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={counts}
              dataKey="value"
              nameKey="name"
              innerRadius={40}
              outerRadius={62}
              paddingAngle={2}
              stroke="none"
            >
              {counts.map((d) => (
                <Cell key={d.severity} fill={severityColor[d.severity]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 12,
              }}
              itemStyle={{ color: 'var(--fg)' }}
              labelStyle={{ color: 'var(--fg)' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="space-y-1.5">
        {counts.map((d) => (
          <li key={d.severity} className="flex items-center gap-2 text-sm">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={{ background: severityColor[d.severity] }}
            />
            <span className="text-fg">{d.name}</span>
            <span className="tabular-nums text-muted">{d.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
