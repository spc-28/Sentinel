import { Info, Loader2, Play, Send, Zap } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeading } from '@/components/layout/AppShell';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { Field, Input, Select, Textarea } from '@/components/ui/Input';
import { usePostAlert } from '@/hooks/usePostAlert';
import { titleCase } from '@/lib/format';
import { CHAOS_SCENARIOS, SEED_SERVICES } from '@/lib/demo';
import type { AlertWebhookBody } from '@/types/api';
import type { AlertSeverity } from '@/types/enums';
import { SEVERITIES } from '@/types/enums';

interface Posted {
  alertId: string;
  title: string;
  service: string;
  grouped: boolean;
  investigationTriggered: boolean;
  method: string | null;
}

export function DemoPage() {
  const mutation = usePostAlert();
  const [recent, setRecent] = useState<Posted[]>([]);
  const [payloadError, setPayloadError] = useState<string | null>(null);

  const [service, setService] = useState<string>(SEED_SERVICES[0]);
  const [severity, setSeverity] = useState<AlertSeverity>('high');
  const [title, setTitle] = useState('High API latency on checkout');
  const [source, setSource] = useState('datadog');
  const [fingerprint, setFingerprint] = useState('');
  const [payloadText, setPayloadText] = useState('');

  async function post(body: AlertWebhookBody) {
    const res = await mutation.mutateAsync(body);
    setRecent((r) =>
      [
        {
          alertId: res.alert_id,
          title: body.title,
          service: body.service ?? '—',
          grouped: res.grouped,
          investigationTriggered: res.investigation_triggered,
          method: res.method,
        },
        ...r,
      ].slice(0, 8),
    );
  }

  function submit() {
    setPayloadError(null);
    let payload: Record<string, unknown> | undefined;
    if (payloadText.trim()) {
      try {
        payload = JSON.parse(payloadText) as Record<string, unknown>;
      } catch {
        setPayloadError('Payload must be valid JSON.');
        return;
      }
    }
    void post({
      service,
      title: title.trim() || 'Untitled alert',
      severity,
      source: source.trim() || undefined,
      fingerprint: fingerprint.trim() || undefined,
      payload,
    });
  }

  function runChaos(scenario: (typeof CHAOS_SCENARIOS)[number]) {
    void post({
      service: scenario.service,
      title: scenario.title,
      severity: scenario.severity,
      source: 'chaos',
      payload: { category: 'ai_pipeline', fault: scenario.key, index: scenario.index },
    });
  }

  return (
    <div>
      <PageHeading
        title="Demo Console"
        description="Drive Sentinel end-to-end: post an alert or fire a scenario, then watch it investigate."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Post alert */}
        <Card>
          <CardHeader title="Post an alert" subtitle="Sends to POST /webhooks/alert" />
          <CardBody className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Service">
                <Select value={service} onChange={(e) => setService(e.target.value)}>
                  {SEED_SERVICES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Severity">
                <Select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as AlertSeverity)}
                >
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>
                      {titleCase(s)}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label="Title">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Source (optional)">
                <Input value={source} onChange={(e) => setSource(e.target.value)} />
              </Field>
              <Field label="Fingerprint (optional)">
                <Input
                  value={fingerprint}
                  onChange={(e) => setFingerprint(e.target.value)}
                  placeholder="dedupe key"
                />
              </Field>
            </div>
            <Field label="Payload JSON (optional)">
              <Textarea
                rows={3}
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                placeholder='{ "threshold": 500, "current": 850 }'
              />
            </Field>
            {payloadError ? <p className="text-xs text-red-500">{payloadError}</p> : null}
            <div className="flex items-center gap-3">
              <Button onClick={submit} disabled={mutation.isPending}>
                {mutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Post alert
              </Button>
            </div>
          </CardBody>
        </Card>

        {/* Chaos scenarios */}
        <Card>
          <CardHeader
            title="Scenarios"
            subtitle="Fire a known AI-pipeline fault (mirrors scripts/chaos.py)"
          />
          <CardBody className="space-y-3">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {CHAOS_SCENARIOS.map((sc) => (
                <button
                  key={sc.key}
                  type="button"
                  onClick={() => runChaos(sc)}
                  disabled={mutation.isPending}
                  className="flex flex-col items-start gap-1 rounded-lg border border-border bg-surface p-3 text-left transition-colors hover:bg-surface-2 disabled:opacity-50"
                >
                  <span className="flex items-center gap-1.5 text-sm font-medium text-fg">
                    <Zap className="h-3.5 w-3.5 text-amber-500" />
                    {sc.label}
                  </span>
                  <span className="text-xs text-muted">{sc.blurb}</span>
                  <span className="font-mono text-[11px] text-muted">{sc.service}</span>
                </button>
              ))}
            </div>
            <div className="flex items-start gap-2 rounded-md border border-border bg-surface-2 p-3 text-xs text-muted">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                Posting the alert drives a real investigation. Deep fault injection into the vector
                index still needs <code className="font-mono">make chaos</code> on the server.
              </span>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Recent activity */}
      <Card className="mt-4">
        <CardHeader title="Just posted" subtitle="Follow each alert into its investigation" />
        <CardBody>
          {recent.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-muted">
              <Play className="h-4 w-4" />
              Post an alert or fire a scenario to see it here.
            </p>
          ) : (
            <div className="space-y-2">
              {recent.map((r, i) => (
                <div
                  key={`${r.alertId}-${i}`}
                  className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-2.5"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg">{r.title}</p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                      <span className="font-mono">{r.service}</span>
                      {r.grouped ? (
                        <Badge className="bg-surface-2 ring-border">
                          grouped{r.method ? ` · ${r.method}` : ''}
                        </Badge>
                      ) : (
                        <Badge className="bg-surface-2 ring-border">new group</Badge>
                      )}
                    </div>
                  </div>
                  {r.investigationTriggered || !r.grouped ? (
                    <Link
                      to={`/watch/${r.alertId}`}
                      className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-fg hover:opacity-90"
                    >
                      Watch investigation
                    </Link>
                  ) : (
                    <span className="text-xs text-muted">merged into open group</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
