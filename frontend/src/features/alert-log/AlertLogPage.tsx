import { PageHeader } from '@/components/shared/PageHeader'
import { Skeleton } from '@/components/ui/skeleton'

export default function AlertLogPage() {
  return (
    <>
      <PageHeader title="AlertLog" description="Coming in a later stage." />
      <Skeleton className="h-64 w-full rounded-2xl" />
    </>
  )
}
