import { Activity, Coins, DollarSign, Cpu } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { PageHeading } from '@/components/layout/AppShell';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { StatCard } from '@/components/ui/StatCard';
import { useIncidentGroups } from '@/hooks/useIncidentGroups';
import { useInvestigationsForGroups } from '@/hooks/useInvestigationsForGroups';
import { useStats } from '@/hooks/useStats';
import { formatCurrency, formatNumber, formatTokens, shortId } from '@/lib/format';

export function CostPage() {
  const stats = useStats();
  const groups = useIncidentGroups();
  const { investigations, isLoading } = useInvestigationsForGroups(groups.data ?? [], 12);

  const chartData = investigations
    .filter((d) => d.investigation.cost_usd != null)
    .map((d) => ({
      name: shortId(d.investigation.id),
      cost: Number(d.investigation.cost_usd),
    }));

  const s = stats.data;
  const avgTokens = s && s.investigations > 0 ? Math.round(s.total_tokens / s.investigations) : 0;
  const costPer1k = s && s.total_tokens > 0 ? (s.total_cost_usd / s.total_tokens) * 1000 : 0;

  return (
    <div>
      <PageHeading
        title="AI Cost & Observability"
        description="What Sentinel's investigations cost in tokens and dollars."
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Investigations"
          value={formatNumber(s?.investigations)}
          icon={<Activity className="h-4 w-4" />}
          loading={stats.isLoading}
        />
        <StatCard
          label="Total cost"
          value={formatCurrency(s?.total_cost_usd)}
          icon={<DollarSign className="h-4 w-4" />}
          loading={stats.isLoading}
        />
        <StatCard
          label="Avg cost"
          value={formatCurrency(s?.avg_cost_usd)}
          hint="per investigation"
          icon={<Coins className="h-4 w-4" />}
          loading={stats.isLoading}
        />
        <StatCard
          label="Total tokens"
          value={formatTokens(s?.total_tokens)}
          icon={<Cpu className="h-4 w-4" />}
          loading={stats.isLoading}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Cost per investigation"
            subtitle="Sample of recent investigations (not a time series)"
          />
          <CardBody>
            {isLoading && chartData.length === 0 ? (
              <SkeletonRows rows={3} />
            ) : chartData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: 'var(--muted)', fontSize: 11 }}
                      tickLine={false}
                      axisLine={{ stroke: 'var(--border)' }}
                    />
                    <YAxis
                      tick={{ fill: 'var(--muted)', fontSize: 11 }}
                      tickLine={false}
                      axisLine={{ stroke: 'var(--border)' }}
                      width={64}
                      tickFormatter={(v: number) => `$${v.toFixed(3)}`}
                    />
                    <Tooltip
                      cursor={{ fill: 'var(--surface-2)' }}
                      contentStyle={{
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      itemStyle={{ color: 'var(--fg)' }}
                      labelStyle={{ color: 'var(--fg)' }}
                      formatter={(v: number) => [`$${v.toFixed(5)}`, 'cost']}
                    />
                    <Bar dataKey="cost" fill="var(--accent)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState
                title="No cost data yet"
                message="Run an investigation from the Demo Console to populate cost metrics."
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Derived metrics" />
          <CardBody className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Avg tokens / investigation</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">
                {formatTokens(avgTokens)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Cost / 1k tokens</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">
                {costPer1k > 0 ? `$${costPer1k.toFixed(4)}` : '—'}
              </p>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
