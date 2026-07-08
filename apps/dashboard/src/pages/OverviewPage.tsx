import { Activity, Coins, DollarSign, Layers, Cpu } from 'lucide-react';
import { Link } from 'react-router-dom';

import { PageHeading } from '@/components/layout/AppShell';
import { LiveFeed } from '@/components/domain/LiveFeed';
import { SeverityDistribution } from '@/components/domain/SeverityDistribution';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { StatCard } from '@/components/ui/StatCard';
import { useIncidentGroups } from '@/hooks/useIncidentGroups';
import { useStats } from '@/hooks/useStats';
import { formatCurrency, formatNumber, formatTokens } from '@/lib/format';

export function OverviewPage() {
  const stats = useStats();
  const groups = useIncidentGroups();

  const openGroups = groups.data?.filter((g) => g.status === 'open').length ?? 0;

  return (
    <div>
      <PageHeading
        title="Overview"
        description="Live view of incidents and AI investigations across your services."
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <StatCard
          label="Investigations"
          value={formatNumber(stats.data?.investigations)}
          icon={<Activity className="h-4 w-4" />}
          loading={stats.isLoading}
        />
        <StatCard
          label="Open groups"
          value={formatNumber(openGroups)}
          icon={<Layers className="h-4 w-4" />}
          loading={groups.isLoading}
        />
        <StatCard
          label="Avg cost"
          value={formatCurrency(stats.data?.avg_cost_usd)}
          hint="per investigation"
          icon={<Coins className="h-4 w-4" />}
          loading={stats.isLoading}
        />
        <StatCard
          label="Total cost"
          value={formatCurrency(stats.data?.total_cost_usd)}
          icon={<DollarSign className="h-4 w-4" />}
          loading={stats.isLoading}
        />
        <StatCard
          label="Total tokens"
          value={formatTokens(stats.data?.total_tokens)}
          icon={<Cpu className="h-4 w-4" />}
          loading={stats.isLoading}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Live feed" subtitle="Most recent incident groups, newest first" />
          <CardBody>
            {groups.isLoading ? (
              <SkeletonRows rows={5} />
            ) : groups.isError ? (
              <ErrorState error={groups.error} onRetry={() => void groups.refetch()} />
            ) : groups.data && groups.data.length > 0 ? (
              <LiveFeed groups={groups.data} />
            ) : (
              <EmptyState
                icon={<Activity className="h-6 w-6" />}
                title="No incidents yet"
                message="Post an alert to watch Sentinel investigate it in real time."
                action={
                  <Link
                    to="/demo"
                    className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:opacity-90"
                  >
                    Open Demo Console
                  </Link>
                }
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Severity mix" subtitle="Across current groups" />
          <CardBody>
            {groups.isLoading ? (
              <SkeletonRows rows={3} />
            ) : (
              <SeverityDistribution groups={groups.data ?? []} />
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
