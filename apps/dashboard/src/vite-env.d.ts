/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_POLL_ACTIVE_MS?: string;
  readonly VITE_POLL_LIST_MS?: string;
  readonly VITE_POLL_STATS_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
