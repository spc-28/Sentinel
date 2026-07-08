export const queryKeys = {
  ready: () => ['ready'] as const,
  groups: () => ['incident-groups'] as const,
  group: (id: string) => ['incident-groups', id] as const,
  incidents: (params: { service?: string; lastNHours?: number }) => ['incidents', params] as const,
  investigation: (id: string) => ['investigation', id] as const,
  investigationByAlert: (alertId: string) => ['investigation-by-alert', alertId] as const,
  stats: () => ['stats'] as const,
  search: (q: string) => ['search', q] as const,
  suggestFix: (id: string) => ['suggest-fix', id] as const,
};
