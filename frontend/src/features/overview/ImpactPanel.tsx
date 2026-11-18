import { Panel } from '@/components/shared/Panel'
import { fmtInt } from '@/lib/format'
import type { Pair, Summary } from '@/lib/types'

function Row({ label, detail, pair }: { label: string; detail: string; pair: Pair }) {
  const max = Math.max(pair.baseline, pair.atc, 1)
  const change = pair.baseline ? Math.round(100 * (1 - pair.atc / pair.baseline)) : 0
  return (
    <li className="py-3.5 first:pt-0 last:pb-0">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-ink">{label}</span>
        <span className="num text-sm text-sent">−{change}%</span>
      </div>
      <p className="mt-0.5 text-xs text-ink-faint">{detail}</p>
      <div className="mt-2.5 space-y-1.5" aria-hidden="true">
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 rounded-full bg-console">
            <div
              className="h-full rounded-full bg-baseline"
              style={{ width: `${(100 * pair.baseline) / max}%` }}
            />
          </div>
          <span className="w-14 text-right num text-xs text-ink-muted">
            {fmtInt(pair.baseline)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 rounded-full bg-console">
            <div
              className="h-full rounded-full bg-sent"
              style={{ width: `${(100 * pair.atc) / max}%` }}
            />
          </div>
          <span className="w-14 text-right num text-xs text-ink">{fmtInt(pair.atc)}</span>
        </div>
      </div>
      <span className="sr-only">
        {fmtInt(pair.baseline)} without ATC, {fmtInt(pair.atc)} with ATC.
      </span>
    </li>
  )
}

export function ImpactPanel({ summary: s }: { summary: Summary }) {
  return (
    <Panel
      title="What customers feel"
      description="Grey is today's stack, teal is with ATC."
      className="h-full"
    >
      <ul className="divide-y divide-rim">
        <Row
          label="Buzzes overnight"
          detail="Push or SMS landing between 10 PM and 7 AM local time"
          pair={s.night_interruptions}
        />
        <Row
          label="Sent to a channel they turned off"
          detail="Alerts that ignored the customer's own preferences"
          pair={s.preference_violations}
        />
        <Row
          label="Marketing messages"
          detail="Offers delivered across all customers"
          pair={s.marketing_delivered}
        />
        <Row
          label="Average fatigue score"
          detail="0–100, alerts felt in the trailing 7 days"
          pair={s.avg_fatigue}
        />
      </ul>
    </Panel>
  )
}
