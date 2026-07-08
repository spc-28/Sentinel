import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/ui/EmptyState';

export function NotFoundPage() {
  return (
    <div className="py-16">
      <EmptyState
        title="Page not found"
        message="That route doesn’t exist."
        action={
          <Link
            to="/"
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg hover:opacity-90"
          >
            Back to Overview
          </Link>
        }
      />
    </div>
  );
}
