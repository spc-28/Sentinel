// Mirror of packages/core/enums.py string enums.

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type AlertStatus = 'received' | 'investigating' | 'resolved' | 'dismissed';
export type IncidentStatus = 'open' | 'mitigated' | 'resolved' | 'closed';
export type InvestigationStatus = 'pending' | 'running' | 'completed' | 'failed';
export type GroupStatus = 'open' | 'closed';
export type EvidenceSource =
  | 'logs'
  | 'metrics'
  | 'traces'
  | 'deploys'
  | 'vectors'
  | 'runbook'
  | 'other';
export type EvidenceStance = 'supporting' | 'refuting' | 'neutral';

export const SEVERITIES: readonly AlertSeverity[] = [
  'critical',
  'high',
  'medium',
  'low',
  'info',
];

export const ACTIVE_INVESTIGATION_STATUSES: readonly InvestigationStatus[] = ['pending', 'running'];
