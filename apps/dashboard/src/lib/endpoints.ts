import { request, requestOrNull } from '@/lib/apiClient';
import type {
  AlertWebhookBody,
  AlertWebhookResponse,
  CostStats,
  IncidentGroupDetail,
  IncidentGroupRead,
  IncidentRead,
  InvestigationDetail,
  PastIncidentRead,
  RCAReportRead,
  ReadyStatus,
  SuggestFix,
} from '@/types/api';

// One typed function per Sentinel endpoint (see apps/api/routers/*).
export const api = {
  getReady: () => request<ReadyStatus>('/ready'),

  listIncidentGroups: () => request<IncidentGroupRead[]>('/incident-groups'),
  getIncidentGroup: (id: string) => request<IncidentGroupDetail>(`/incident-groups/${id}`),

  listIncidents: (params: { service?: string; lastNHours?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.service) q.set('service', params.service);
    if (params.lastNHours != null) q.set('last_n_hours', String(params.lastNHours));
    const qs = q.toString();
    return request<IncidentRead[]>(`/incidents${qs ? `?${qs}` : ''}`);
  },

  getInvestigation: (id: string) => request<InvestigationDetail>(`/investigations/${id}`),
  getInvestigationByAlert: (alertId: string) =>
    requestOrNull<InvestigationDetail>(`/investigations/by-alert/${alertId}`),
  getStats: () => request<CostStats>('/investigations/stats'),
  searchInvestigations: (q: string) =>
    request<RCAReportRead[]>(`/investigations/search?q=${encodeURIComponent(q)}`),
  getSuggestFix: (id: string) => request<SuggestFix>(`/investigations/${id}/suggest-fix`),

  postAlert: (body: AlertWebhookBody) =>
    request<AlertWebhookResponse>('/webhooks/alert', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  confirmCause: (id: string, cause: string) =>
    request<PastIncidentRead>(`/investigations/${id}/confirm-cause`, {
      method: 'POST',
      body: JSON.stringify({ cause }),
    }),
};
