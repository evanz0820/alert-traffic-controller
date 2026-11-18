import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import OverviewPage from '@/features/overview/OverviewPage'
import { Shell } from './Shell'

const LiveTowerPage = lazy(() => import('@/features/tower/LiveTowerPage'))
const RulesLabPage = lazy(() => import('@/features/rules-lab/RulesLabPage'))
const CustomersPage = lazy(() => import('@/features/customers/CustomersPage'))
const AlertLogPage = lazy(() => import('@/features/alert-log/AlertLogPage'))
const AboutPage = lazy(() => import('@/features/about/AboutPage'))

function PageFallback() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading page">
      <Skeleton className="h-9 w-64" />
      <Skeleton className="h-5 w-96 max-w-full" />
      <Skeleton className="mt-6 h-72 w-full rounded-2xl" />
    </div>
  )
}

const page = (node: ReactNode) => <Suspense fallback={<PageFallback />}>{node}</Suspense>

export const router = createBrowserRouter([
  {
    element: <Shell />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'tower', element: page(<LiveTowerPage />) },
      { path: 'rules', element: page(<RulesLabPage />) },
      { path: 'customers', element: page(<CustomersPage />) },
      { path: 'log', element: page(<AlertLogPage />) },
      { path: 'about', element: page(<AboutPage />) },
    ],
  },
])
