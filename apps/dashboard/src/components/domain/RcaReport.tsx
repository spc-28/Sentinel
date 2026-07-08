import { ClipboardList, Target, Wrench } from 'lucide-react';
import type { ReactNode } from 'react';

import { Markdown } from '@/components/ui/Markdown';
import type { RCAReportRead } from '@/types/api';
import { TimelineList } from './TimelineList';

function Section({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
        {icon}
        {title}
      </div>
      {children}
    </div>
  );
}

export function RcaReport({ report }: { report: RCAReportRead }) {
  // `summary` is the full rendered markdown doc (root cause + timeline + fix); we
  // present those as clean structured sections instead, so it's intentionally unused.
  return (
    <div className="space-y-5">
      <Section icon={<Target className="h-3.5 w-3.5" />} title="Root cause">
        <div className="rounded-md border border-border bg-surface-2 p-3">
          <Markdown>{report.root_cause}</Markdown>
        </div>
      </Section>

      <Section icon={<ClipboardList className="h-3.5 w-3.5" />} title="Timeline">
        <TimelineList timeline={report.timeline} />
      </Section>

      {report.recommended_fix ? (
        <Section icon={<Wrench className="h-3.5 w-3.5" />} title="Recommended fix">
          <Markdown>{report.recommended_fix}</Markdown>
        </Section>
      ) : null}
    </div>
  );
}
