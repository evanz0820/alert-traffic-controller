import { FlowBars } from '@/components/charts/FlowBars'
import { FlowSankey } from '@/components/charts/FlowSankey'
import { VolumeChart } from '@/components/charts/VolumeChart'
import { ErrorState } from '@/components/shared/ErrorState'
import { Panel } from '@/components/shared/Panel'
import { Skeleton } from '@/components/ui/skeleton'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { fmtInt } from '@/lib/format'
import { useFlows, useSummary, useTimeseries } from '@/lib/queries'
import type { Summary } from '@/lib/types'
import { describeFlows } from './flowSummary'
import { ImpactPanel } from './ImpactPanel'
import { KpiStrip } from './KpiStrip'

function Hero({ summary: s }: { summary: Summary }) {
  return (
    <header className="mb-8 max-w-[62ch]">
      <h1 className="text-[28px] leading-[1.2] font-semibold tracking-tight text-balance text-ink sm:text-[36px]">
        ATC cut alert volume <span className="num font-medium">{s.reduction_pct.toFixed(0)}%</span>{' '}
        while delivering <span className="num font-medium">{s.critical.rate.toFixed(0)}%</span> of{' '}
        <span className="num font-medium">{fmtInt(s.critical.requested)}</span> critical alerts.
      </h1>
      <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">
        Same {s.days} days, same {fmtInt(s.customers)} Northgate customers, same{' '}
        {fmtInt(s.requested)} alert requests. One pass sends everything the way today's systems do;
        the other routes every alert through the controller.
      </p>
    </header>
  )
}

function OverviewSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading results">
      <Skeleton className="h-10 w-full max-w-2xl" />
      <Skeleton className="mt-3 h-5 w-full max-w-xl" />
      <Skeleton className="mt-8 h-32 w-full rounded-2xl" />
      <Skeleton className="mt-6 h-[640px] w-full rounded-2xl" />
    </div>
  )
}

export default function OverviewPage() {
  const summary = useSummary()
  const flows = useFlows()
  const series = useTimeseries()
  const wide = useMediaQuery('(min-width: 900px)')

  if (summary.isError) return <ErrorState error={summary.error} onRetry={() => summary.refetch()} />
  if (!summary.data) return <OverviewSkeleton />
  const s = summary.data

  return (
    <>
      <Hero summary={s} />
      <KpiStrip summary={s} />

      <Panel
        className="mt-6"
        title="Where every alert went"
        description={
          wide
            ? 'Event type on the left, the rule that decided its fate in the middle, the outcome on the right. Hover a band for counts.'
            : 'Each bar is one rule: how many alerts it decided, split by the outcome it gave them.'
        }
      >
        {flows.data ? (
          <figure>
            {wide ? <FlowSankey data={flows.data} /> : <FlowBars data={flows.data} />}
            <figcaption className="mt-5 max-w-[80ch] space-y-1 border-t border-rim pt-4 text-sm text-ink-muted">
              {describeFlows(flows.data).map((line) => (
                <p key={line}>{line}</p>
              ))}
            </figcaption>
          </figure>
        ) : (
          <Skeleton className="h-[600px] w-full" />
        )}
      </Panel>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Panel
          className="flex flex-col"
          bodyClassName="flex flex-1 flex-col"
          title="Daily alerts delivered"
          description="Dashed grey is without ATC; teal is with ATC; red is critical alerts, which never change."
        >
          {series.data ? (
            <figure className="flex min-h-[280px] flex-1 flex-col">
              <VolumeChart data={series.data} />
              <figcaption className="sr-only">
                Daily delivered alerts over {series.data.length} days. Without ATC averages{' '}
                {fmtInt(series.data.reduce((a, p) => a + p.baseline, 0) / series.data.length)} per
                day; with ATC averages{' '}
                {fmtInt(series.data.reduce((a, p) => a + p.atc, 0) / series.data.length)} per day.
              </figcaption>
            </figure>
          ) : (
            <Skeleton className="h-[280px] w-full" />
          )}
        </Panel>
        <ImpactPanel summary={s} />
      </div>
    </>
  )
}
