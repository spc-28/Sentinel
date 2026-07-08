import { Loader2 } from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { useInvestigationByAlert } from '@/hooks/useInvestigation';

// Bridges a freshly-posted alert to its investigation: polls by-alert until the
// worker opens the investigation, then redirects to the detail view.
export function WatchAlertPage() {
  const { alertId = '' } = useParams();
  const navigate = useNavigate();
  const { data } = useInvestigationByAlert(alertId);

  useEffect(() => {
    if (data) navigate(`/investigations/${data.investigation.id}`, { replace: true });
  }, [data, navigate]);

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
      <Loader2 className="h-6 w-6 animate-spin text-accent" />
      <p className="text-sm font-medium text-fg">Waiting for the worker to open the investigation…</p>
      <p className="text-xs text-muted">
        The alert was accepted. This resolves automatically once the investigation starts.
      </p>
    </div>
  );
}
