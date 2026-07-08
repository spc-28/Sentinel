import { formatDateTime } from '@/lib/format';

// report.timeline is list[dict[str, Any]] — untyped. Render known keys when
// present, otherwise fall back to a readable dump of the object.
const TIME_KEYS = ['at', 'time', 'timestamp', 'ts', 'when'];
const TITLE_KEYS = ['event', 'title', 'label', 'name', 'step'];
const DETAIL_KEYS = ['detail', 'description', 'note', 'message', 'summary'];

function pick(entry: Record<string, unknown>, keys: string[]): string | null {
  for (const k of keys) {
    const v = entry[k];
    if (typeof v === 'string' && v.trim()) return v;
    if (typeof v === 'number') return String(v);
  }
  return null;
}

function rest(entry: Record<string, unknown>, used: Set<string>): string | null {
  const extra = Object.fromEntries(Object.entries(entry).filter(([k]) => !used.has(k)));
  const keys = Object.keys(extra);
  if (keys.length === 0) return null;
  return JSON.stringify(extra);
}

export function TimelineList({ timeline }: { timeline: Array<Record<string, unknown>> }) {
  if (!timeline || timeline.length === 0) {
    return <p className="text-xs text-muted">No timeline recorded.</p>;
  }
  return (
    <ol className="space-y-3">
      {timeline.map((entry, i) => {
        const time = pick(entry, TIME_KEYS);
        const title = pick(entry, TITLE_KEYS);
        const detail = pick(entry, DETAIL_KEYS);
        const used = new Set([...TIME_KEYS, ...TITLE_KEYS, ...DETAIL_KEYS]);
        const extra = title || detail ? rest(entry, used) : JSON.stringify(entry);
        return (
          <li key={i} className="relative pl-5">
            <span className="absolute left-0 top-1.5 h-2 w-2 rounded-full bg-accent/60" />
            {time ? (
              <span className="text-[11px] font-medium tabular-nums text-muted">
                {formatDateTime(time)}
              </span>
            ) : null}
            {title ? <p className="text-sm font-medium text-fg">{title}</p> : null}
            {detail ? <p className="text-xs leading-relaxed text-muted">{detail}</p> : null}
            {extra ? (
              <p className="mt-0.5 break-words font-mono text-[11px] text-muted">{extra}</p>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
