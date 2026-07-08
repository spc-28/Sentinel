import { createBrowserRouter } from 'react-router-dom';

import { RootLayout } from '@/App';
import { CostPage } from '@/pages/CostPage';
import { DemoPage } from '@/pages/DemoPage';
import { IncidentGroupDetailPage } from '@/pages/IncidentGroupDetailPage';
import { IncidentGroupsPage } from '@/pages/IncidentGroupsPage';
import { InvestigationDetailPage } from '@/pages/InvestigationDetailPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { OverviewPage } from '@/pages/OverviewPage';
import { WatchAlertPage } from '@/pages/WatchAlertPage';

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: '/', element: <OverviewPage /> },
      { path: '/groups', element: <IncidentGroupsPage /> },
      { path: '/groups/:id', element: <IncidentGroupDetailPage /> },
      { path: '/investigations/:id', element: <InvestigationDetailPage /> },
      { path: '/cost', element: <CostPage /> },
      { path: '/demo', element: <DemoPage /> },
      { path: '/watch/:alertId', element: <WatchAlertPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
