// Mirror of packages/core/schemas.py response models. Every *Read model inherits
// the shared id + created_at + updated_at base. Timestamps/UUIDs are ISO strings;
// free-form JSON (payload, timeline) is intentionally left as Record<string, unknown>.

import type {
  AlertSeverity,
  AlertStatus,
  GroupStatus,
  IncidentStatus,
  InvestigationStatus,
} from './enums';

export interface ReadBase {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface IncidentGroupRead extends ReadBase {
  title: string;
  service_id: string | null;
  severity: AlertSeverity;
  status: GroupStatus;
  leader_alert_id: string | null;
  last_activity_at: string;
  alert_count: number;
}

export interface AlertRead extends ReadBase {
  service_id: string | null;
  title: string;
  severity: AlertSeverity;
  source: string | null;
  fingerprint: string | null;
  payload: Record<string, unknown>;
  triggered_at: string | null;
  status: AlertStatus;
}

export interface IncidentGroupDetail {
  group: IncidentGroupRead;
  alerts: AlertRead[];
}

export interface IncidentRead extends ReadBase {
  alert_id: string;
  service_id: string | null;
  title: string;
  status: IncidentStatus;
  started_at: string | null;
  resolved_at: string | null;
}

export interface InvestigationRead extends ReadBase {
  incident_id: string;
  status: InvestigationStatus;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  cost_usd: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
}

export interface HypothesisRead extends ReadBase {
  investigation_id: string;
  statement: string;
  description: string | null;
  confidence: number;
  rank: number;
}

export interface RCAReportRead extends ReadBase {
  investigation_id: string;
  summary: string | null;
  root_cause: string;
  timeline: Array<Record<string, unknown>>;
  recommended_fix: string | null;
}

export interface InvestigationDetail {
  investigation: InvestigationRead;
  hypotheses: HypothesisRead[];
  report: RCAReportRead | null;
}

export interface CostStats {
  investigations: number;
  avg_cost_usd: number;
  total_cost_usd: number;
  total_tokens: number;
}

export interface SuggestFix {
  investigation_id: string;
  root_cause: string | null;
  recommended_fix: string | null;
  revert_pr_url: string | null;
  revert_title: string | null;
  note: string;
}

export interface PastIncidentRead extends ReadBase {
  service: string;
  alert_type: string;
  fingerprint: string;
  title: string;
  root_cause: string;
  recommended_fix: string | null;
  confirmed_cause: string | null;
  match_score: number | null;
  weight: number;
  occurrences: number;
  is_pattern: boolean;
  pattern_label: string | null;
}

// Request body for POST /webhooks/alert (packages/core/schemas.py:AlertWebhook).
export interface AlertWebhookBody {
  service?: string;
  title: string;
  severity: AlertSeverity;
  source?: string;
  fingerprint?: string;
  triggered_at?: string;
  payload?: Record<string, unknown>;
}

export interface AlertWebhookResponse {
  status: string;
  alert_id: string;
  group_id: string;
  grouped: boolean;
  method: string | null;
  investigation_triggered: boolean;
}

export interface ReadyStatus {
  status: string;
  checks: { postgres: boolean; redis: boolean };
}
