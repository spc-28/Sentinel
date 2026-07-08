import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { cn } from '@/lib/cn';

// Renders LLM-authored markdown (root cause, fixes) with the theme's typography.
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div
      className={cn(
        'prose prose-sm max-w-none dark:prose-invert',
        'prose-headings:font-semibold prose-headings:text-fg prose-p:text-fg',
        'prose-li:text-fg prose-strong:text-fg prose-code:text-fg',
        'prose-code:rounded prose-code:bg-surface-2 prose-code:px-1 prose-code:py-0.5',
        'prose-code:before:content-none prose-code:after:content-none',
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
