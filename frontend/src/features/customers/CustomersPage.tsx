import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { ErrorState } from '@/components/shared/ErrorState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { SEGMENT_LABEL, zoneLabel } from '@/lib/format'
import { useCustomers } from '@/lib/queries'
import type { CustomerListItem } from '@/lib/types'
import { CustomerSheet } from './CustomerSheet'

type Sort = 'fatigue' | 'relief' | 'name'

const SORTS: Record<
  Sort,
  { label: string; compare: (a: CustomerListItem, b: CustomerListItem) => number }
> = {
  fatigue: {
    label: 'Most fatigued before ATC',
    compare: (a, b) => (b.fatigue_baseline ?? 0) - (a.fatigue_baseline ?? 0),
  },
  relief: {
    label: 'Biggest drop in fatigue',
    compare: (a, b) =>
      (b.fatigue_baseline ?? 0) -
      (b.fatigue_atc ?? 0) -
      ((a.fatigue_baseline ?? 0) - (a.fatigue_atc ?? 0)),
  },
  name: { label: 'Name', compare: (a, b) => a.name.localeCompare(b.name) },
}

function FatigueCell({ before, after }: { before: number; after: number }) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-1.5 w-16 rounded-full bg-console sm:w-28" aria-hidden="true">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-baseline/60"
          style={{ width: `${before}%` }}
        />
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-sent"
          style={{ width: `${after}%` }}
        />
      </div>
      <span className="num text-xs whitespace-nowrap text-ink-muted">
        {before.toFixed(0)} <span className="text-ink-faint">to</span>{' '}
        <span className="text-ink">{after.toFixed(0)}</span>
      </span>
    </div>
  )
}

export default function CustomersPage() {
  const [params, setParams] = useSearchParams()
  const selected = params.get('id') ? Number(params.get('id')) : null
  const customers = useCustomers()
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState('all')
  const [sort, setSort] = useState<Sort>('fatigue')

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (customers.data ?? [])
      .filter((c) => segment === 'all' || c.segment === segment)
      .filter((c) => !q || c.name.toLowerCase().includes(q) || String(c.id) === q)
      .sort(SORTS[sort].compare)
  }, [customers.data, query, segment, sort])

  const open = (id: number) => setParams({ id: String(id) })
  const close = () => setParams({})

  return (
    <>
      <PageHeader
        title="Customers"
        description="Pick anyone to see the alerts they'd get today next to what ATC actually sent, with every decision explained."
      />

      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative lg:w-72">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-faint" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or ID"
            aria-label="Search customers"
            className="bg-deck pl-9"
          />
        </div>
        <ToggleGroup
          type="single"
          value={segment}
          onValueChange={(v) => v && setSegment(v)}
          variant="outline"
          aria-label="Segment"
          className="flex-wrap"
        >
          <ToggleGroupItem value="all">All</ToggleGroupItem>
          {Object.entries(SEGMENT_LABEL).map(([key, label]) => (
            <ToggleGroupItem key={key} value={key}>
              {label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <div className="lg:ml-auto">
          <Select value={sort} onValueChange={(v) => setSort(v as Sort)}>
            <SelectTrigger aria-label="Sort customers" className="w-full bg-deck lg:w-60">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(SORTS).map(([key, s]) => (
                <SelectItem key={key} value={key}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {customers.isError ? (
        <ErrorState error={customers.error} onRetry={() => customers.refetch()} />
      ) : !customers.data ? (
        <Skeleton className="h-[600px] w-full rounded-2xl" />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-rim bg-deck">
          <div className="hidden grid-cols-[minmax(0,1.6fr)_1fr_1fr_1fr_minmax(0,1.4fr)] gap-4 border-b border-rim px-5 py-3 text-xs text-ink-faint md:grid">
            <span>Customer</span>
            <span>Segment</span>
            <span>Time zone</span>
            <span>App engagement</span>
            <span>Fatigue, before to after</span>
          </div>
          {rows.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-ink-muted">
              No customers match "{query}". Try a different name or clear the segment filter.
            </p>
          ) : (
            <ul className="max-h-[70dvh] divide-y divide-rim overflow-y-auto">
              {rows.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => open(c.id)}
                    className="grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 px-5 py-3 text-left text-sm transition-colors hover:bg-console/60 focus-visible:bg-console md:grid-cols-[minmax(0,1.6fr)_1fr_1fr_1fr_minmax(0,1.4fr)] md:items-center"
                  >
                    <span className="min-w-0 truncate text-ink">
                      {c.name} <span className="ml-1 num text-xs text-ink-faint">#{c.id}</span>
                    </span>
                    <span className="text-ink-muted max-md:hidden">{SEGMENT_LABEL[c.segment]}</span>
                    <span className="text-ink-muted max-md:hidden">{zoneLabel(c.timezone)}</span>
                    <span className="text-ink-muted capitalize max-md:hidden">{c.engagement}</span>
                    <span className="max-md:row-span-2 max-md:self-center">
                      {c.fatigue_baseline === null || c.fatigue_atc === null ? (
                        <span className="text-xs text-ink-faint">No data</span>
                      ) : (
                        <FatigueCell before={c.fatigue_baseline} after={c.fatigue_atc} />
                      )}
                    </span>
                    <span className="text-xs text-ink-faint md:hidden">
                      {SEGMENT_LABEL[c.segment]}, {zoneLabel(c.timezone)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <p className="mt-3 text-xs text-ink-faint">
        Showing {rows.length} of {customers.data?.length ?? 0} customers. Press ⌘K to jump to
        anyone.
      </p>

      <CustomerSheet id={selected} onClose={close} />
    </>
  )
}
