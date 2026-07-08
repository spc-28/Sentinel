interface AppConfig {
  apiUrl: string;
  pollActiveMs: number;
  pollListMs: number;
  pollStatsMs: number;
}

function num(value: string | undefined, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

export const config: AppConfig = {
  apiUrl: import.meta.env.VITE_API_URL ?? '/api',
  pollActiveMs: num(import.meta.env.VITE_POLL_ACTIVE_MS, 2000),
  pollListMs: num(import.meta.env.VITE_POLL_LIST_MS, 8000),
  pollStatsMs: num(import.meta.env.VITE_POLL_STATS_MS, 15000),
};
