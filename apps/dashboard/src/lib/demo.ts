import type { AlertSeverity } from '@/types/enums';

// Seed services (scripts/seed.py) — used to populate the demo alert form.
export const SEED_SERVICES = [
  'checkout-api',
  'auth-service',
  'search-api',
  'notifications-worker',
  'inventory-service',
] as const;

export interface ChaosScenario {
  key: string;
  label: string;
  service: string;
  title: string;
  index: string;
  severity: AlertSeverity;
  blurb: string;
}

// Mirrors scripts/chaos.py: posting the matching alert drives an investigation.
// (Deep Qdrant fault injection still requires `make chaos` on the server.)
export const CHAOS_SCENARIOS: ChaosScenario[] = [
  {
    key: 'embedding_drift',
    label: 'Embedding drift',
    service: 'search-api',
    title: 'Embedding drift suspected on runbooks index',
    index: 'runbooks',
    severity: 'high',
    blurb: 'Vector distribution drifts on the runbooks index.',
  },
  {
    key: 'search_quality',
    label: 'RAG quality drop',
    service: 'search-api',
    title: 'RAG answer quality dropped',
    index: 'runbooks',
    severity: 'high',
    blurb: 'Retrieval answers lose faithfulness to context.',
  },
  {
    key: 'prompt_regression',
    label: 'Prompt regression',
    service: 'checkout-api',
    title: 'Prompt regression after deploy',
    index: 'runbooks',
    severity: 'high',
    blurb: 'A shipped prompt scores worse than the prior version.',
  },
  {
    key: 'cost_spike',
    label: 'AI cost spike',
    service: 'checkout-api',
    title: 'AI cost spike detected',
    index: 'runbooks',
    severity: 'high',
    blurb: 'Hourly AI spend jumps above the baseline.',
  },
];
