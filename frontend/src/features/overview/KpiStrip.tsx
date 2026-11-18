import { ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { CountUp } from '@/components/shared/CountUp'
import { fmtInt } from '@/lib/format'
import type { Summary } from '@/lib/types'
import { cn } from '@/lib/utils'

const asInt = (n: number) => fmtInt(n)
const asPct = (n: number) => `${n.toFixed(1)}%`
const asRate = (n: number) => `${n.toFixed(0)}%`
const asDec2 = (n: number) => n.toFixed(2)
const asSeconds = (n: number) => `${n.toFixed(2)}s`

function Reading({
  label,
  value,
  format,
  compare,
  tone,
  icon,
}: {
  label: string
  value: number
  format: (n: number) => string
  compare: ReactNode
  tone?: 'critical' | 'sent'
  icon?: ReactNode
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2 px-5 py-5 sm:px-6">
      <div className="flex items-center gap-1.5 text-[13px] text-ink-muted">
        {icon}
        {label}
      </div>
      <CountUp
        value={value}
        format={format}
        className={cn(
          'num text-[28px] leading-none font-medium tracking-tight text-ink',
          tone === 'critical' && 'text-critical',
          tone === 'sent' && 'text-sent',
        )}
      />
      <div className="text-xs text-ink-faint">{compare}</div>
    </div>
  )
}

/** Six readings on one instrument strip, separated by hairlines rather than boxed separately. */
export function KpiStrip({ summary: s }: { summary: Summary }) {
  return (
    <section
      aria-label="Headline results"
      className="grid grid-cols-2 divide-rim overflow-hidden rounded-2xl border border-rim bg-deck md:grid-cols-3 xl:grid-cols-6 [&>*]:border-rim xl:[&>*:not(:last-child)]:border-r md:max-xl:[&>*:not(:nth-child(3n))]:border-r md:max-xl:[&>*:nth-child(-n+3)]:border-b max-md:[&>*:nth-child(-n+4)]:border-b max-md:[&>*:nth-child(odd)]:border-r"
    >
      <Reading
        label="Alerts requested"
        value={s.requested}
        format={asInt}
        compare={<>by upstream systems in {s.days} days</>}
      />
      <Reading
        label="Alerts delivered"
        value={s.delivered.atc}
        format={asInt}
        compare={
          <>
            <span className="num">{fmtInt(s.delivered.baseline)}</span> without ATC
          </>
        }
      />
      <Reading
        label="Volume reduction"
        value={s.reduction_pct}
        format={asPct}
        tone="sent"
        compare={
          <>
            <span className="num">{fmtInt(s.delivered.baseline - s.delivered.atc)}</span> fewer
            interruptions
          </>
        }
      />
      <Reading
        label="Per customer per day"
        value={s.per_customer_day.atc}
        format={asDec2}
        compare={
          <>
            down from <span className="num">{s.per_customer_day.baseline.toFixed(2)}</span>
          </>
        }
      />
      <Reading
        label="Critical delivered"
        value={s.critical.rate}
        format={asRate}
        tone="critical"
        icon={<ShieldCheck className="size-3.5 text-critical" aria-hidden="true" />}
        compare={
          <>
            <span className="num">
              {fmtInt(s.critical.delivered)} of {fmtInt(s.critical.requested)}
            </span>
            , none held or dropped
          </>
        }
      />
      <Reading
        label="Median critical latency"
        value={s.critical.median_latency_s}
        format={asSeconds}
        compare={<>from event to first channel</>}
      />
    </section>
  )
}
