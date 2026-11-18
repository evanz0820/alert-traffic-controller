import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type PaginationState,
} from '@tanstack/react-table'
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { ErrorState } from '@/components/shared/ErrorState'
import { OutcomeBadge, PriorityDot, RuleBadge } from '@/components/shared/OutcomeBadge'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import {
  EVENT_LABEL,
  fmtDateTime,
  fmtInt,
  OUTCOME_LABEL,
  PRIORITY_LABEL,
  RULE_LABEL,
} from '@/lib/format'
import { useAlerts } from '@/lib/queries'
import { useRun } from '@/lib/run-context'
import type { AlertFilters, AlertRow, Outcome, Priority, RuleKey } from '@/lib/types'
import { FilterMenu } from './FilterMenu'

const TZ = 'America/New_York'
const col = createColumnHelper<AlertRow>()

const options = <T extends string>(labels: Record<T, string>) =>
  (Object.entries(labels) as [T, string][]).map(([value, label]) => ({ value, label }))

const columns = [
  col.accessor('requested_at', {
    header: 'Requested, ET',
    cell: (c) => (
      <span className="num text-xs whitespace-nowrap text-ink-muted">
        {fmtDateTime(c.getValue(), TZ)}
      </span>
    ),
  }),
  col.accessor('customer_name', {
    header: 'Customer',
    cell: (c) => (
      <span className="whitespace-nowrap text-ink">
        {c.getValue()}{' '}
        <span className="num text-xs text-ink-faint">#{c.row.original.customer_id}</span>
      </span>
    ),
  }),
  col.accessor('event_type', {
    header: 'Event',
    cell: (c) => (
      <span className="flex items-center gap-2 whitespace-nowrap">
        <PriorityDot priority={c.row.original.priority} />
        <span className={c.row.original.priority === 'critical' ? 'text-critical' : 'text-ink'}>
          {EVENT_LABEL[c.getValue()]}
        </span>
      </span>
    ),
  }),
  col.display({
    id: 'channel',
    header: 'Channel',
    cell: (c) => {
      const r = c.row.original
      const final = r.channels.length ? r.channels.join(' + ') : '—'
      return (
        <span className="text-xs whitespace-nowrap text-ink-muted">
          {r.requested_channel === final ? final : `${r.requested_channel} → ${final}`}
        </span>
      )
    },
  }),
  col.accessor('outcome', {
    header: 'Outcome',
    cell: (c) => <OutcomeBadge outcome={c.getValue()} priority={c.row.original.priority} />,
  }),
  col.accessor('decided_by_rule', {
    header: 'Rule',
    cell: (c) => <RuleBadge rule={c.getValue()} />,
  }),
  col.accessor('reason', {
    header: 'Why',
    cell: (c) => (
      <span
        className="line-clamp-2 min-w-64 text-xs leading-relaxed text-ink-muted"
        title={c.getValue()}
      >
        {c.getValue()}
      </span>
    ),
  }),
]

const EMPTY: AlertFilters = {}

export default function AlertLogPage() {
  const { runId } = useRun()
  const [filters, setFilters] = useState<AlertFilters>(EMPTY)
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 25 })
  const [desc, setDesc] = useState(false)
  const alerts = useAlerts(
    filters,
    pagination.pageIndex + 1,
    pagination.pageSize,
    desc ? '-requested_at' : 'requested_at',
  )

  const update = (patch: Partial<AlertFilters>) => {
    setFilters((f) => ({ ...f, ...patch }))
    setPagination((p) => ({ ...p, pageIndex: 0 }))
  }

  const data = useMemo(() => alerts.data?.items ?? [], [alerts.data])
  // TanStack Table returns mutable instances the React Compiler can't memoize; this is expected.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    rowCount: alerts.data?.total ?? 0,
    state: { pagination },
    onPaginationChange: setPagination,
    getRowId: (r) => r.alert_id,
  })

  const active = Object.values(filters).some((v) => (Array.isArray(v) ? v.length : v))
  const total = alerts.data?.total ?? 0
  const first = total ? pagination.pageIndex * pagination.pageSize + 1 : 0
  const last = Math.min(total, (pagination.pageIndex + 1) * pagination.pageSize)

  return (
    <>
      <PageHeader
        title="Alert Log"
        description="Every decision the controller made, with the rule that made it and why. Filter, page through, or export what you see."
        actions={
          runId && (
            <Button variant="outline" asChild>
              <a href={api.alertsCsvUrl(runId, filters)} download>
                <Download /> Export CSV
              </a>
            </Button>
          )
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <FilterMenu<Outcome>
          label="Outcome"
          options={options(OUTCOME_LABEL)}
          selected={filters.outcome ?? []}
          onChange={(outcome) => update({ outcome })}
        />
        <FilterMenu<RuleKey>
          label="Rule"
          options={options(RULE_LABEL)}
          selected={filters.rule ?? []}
          onChange={(rule) => update({ rule })}
        />
        <FilterMenu<Priority>
          label="Priority"
          options={options(PRIORITY_LABEL)}
          selected={filters.priority ?? []}
          onChange={(priority) => update({ priority })}
        />
        <FilterMenu<string>
          label="Event"
          options={options(EVENT_LABEL)}
          selected={filters.event_type ?? []}
          onChange={(event_type) => update({ event_type })}
        />
        <div className="flex items-center gap-1.5">
          <label htmlFor="from" className="text-xs text-ink-faint">
            From
          </label>
          <Input
            id="from"
            type="date"
            min="2026-10-19"
            max="2026-11-17"
            value={filters.date_from?.slice(0, 10) ?? ''}
            onChange={(e) =>
              update({ date_from: e.target.value ? `${e.target.value}T00:00:00Z` : undefined })
            }
            className="h-8 w-[9.5rem] bg-deck text-xs"
          />
          <label htmlFor="to" className="text-xs text-ink-faint">
            to
          </label>
          <Input
            id="to"
            type="date"
            min="2026-10-19"
            max="2026-11-17"
            value={
              filters.date_to
                ? new Date(new Date(filters.date_to).getTime() - 864e5).toISOString().slice(0, 10)
                : ''
            }
            onChange={(e) =>
              update({
                date_to: e.target.value
                  ? new Date(
                      new Date(`${e.target.value}T00:00:00Z`).getTime() + 864e5,
                    ).toISOString()
                  : undefined,
              })
            }
            className="h-8 w-[9.5rem] bg-deck text-xs"
          />
        </div>
        <Input
          inputMode="numeric"
          placeholder="Customer ID"
          aria-label="Customer ID"
          value={filters.customer_id ?? ''}
          onChange={(e) => {
            const n = Number(e.target.value.replace(/\D/g, ''))
            update({ customer_id: n > 0 ? n : undefined })
          }}
          className="h-8 w-28 bg-deck text-xs"
        />
        {active && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              update({ ...Object.fromEntries(Object.keys(filters).map((k) => [k, undefined])) })
            }
          >
            <X /> Clear filters
          </Button>
        )}
      </div>

      {alerts.isError ? (
        <ErrorState error={alerts.error} onRetry={() => alerts.refetch()} />
      ) : !alerts.data ? (
        <Skeleton className="h-[640px] w-full rounded-2xl" />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-rim bg-deck">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <caption className="sr-only">
                Alert decisions, {fmtInt(total)} matching, page {pagination.pageIndex + 1}
              </caption>
              <thead>
                {table.getHeaderGroups().map((group) => (
                  <tr
                    key={group.id}
                    className="border-b border-rim text-left text-xs text-ink-faint"
                  >
                    {group.headers.map((header) => (
                      <th
                        key={header.id}
                        scope="col"
                        className="px-4 py-3 font-normal whitespace-nowrap"
                      >
                        {header.id === 'requested_at' ? (
                          <button
                            type="button"
                            onClick={() => {
                              setDesc((d) => !d)
                              setPagination((p) => ({ ...p, pageIndex: 0 }))
                            }}
                            className="inline-flex items-center gap-1 hover:text-ink"
                            aria-label={`Sort by time, currently ${desc ? 'newest' : 'oldest'} first`}
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            {desc ? (
                              <ArrowDown className="size-3" />
                            ) : (
                              <ArrowUp className="size-3" />
                            )}
                          </button>
                        ) : (
                          flexRender(header.column.columnDef.header, header.getContext())
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className={alerts.isPlaceholderData ? 'opacity-60' : undefined}>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-rim last:border-0 hover:bg-console/40"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-2.5 align-top">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="divide-y divide-rim md:hidden">
            {data.map((r) => (
              <li key={r.alert_id} className="space-y-1.5 px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-sm">
                    <PriorityDot priority={r.priority} />
                    <span className={r.priority === 'critical' ? 'text-critical' : 'text-ink'}>
                      {EVENT_LABEL[r.event_type]}
                    </span>
                  </span>
                  <OutcomeBadge outcome={r.outcome} priority={r.priority} />
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-faint">
                  <span className="num">{fmtDateTime(r.requested_at, TZ)} ET</span>
                  <span>{r.customer_name}</span>
                  <RuleBadge rule={r.decided_by_rule} />
                </div>
                <p className="text-xs leading-relaxed text-ink-muted">{r.reason}</p>
              </li>
            ))}
          </ul>

          {data.length === 0 && (
            <p className="px-5 py-12 text-center text-sm text-ink-muted">
              No decisions match these filters. Clear a filter to see more.
            </p>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-rim px-4 py-3 text-xs text-ink-muted">
            <span className="num" aria-live="polite">
              {fmtInt(first)}–{fmtInt(last)} of {fmtInt(total)}
            </span>
            <div className="flex items-center gap-2">
              <Select
                value={String(pagination.pageSize)}
                onValueChange={(v) => setPagination({ pageIndex: 0, pageSize: Number(v) })}
              >
                <SelectTrigger size="sm" aria-label="Rows per page" className="w-[7.5rem] bg-deck">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[25, 50, 100].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n} per page
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="icon-sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                aria-label="Previous page"
              >
                <ChevronLeft />
              </Button>
              <span className="px-1 num">
                {pagination.pageIndex + 1} / {fmtInt(Math.max(1, table.getPageCount()))}
              </span>
              <Button
                variant="outline"
                size="icon-sm"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                aria-label="Next page"
              >
                <ChevronRight />
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
