import { Panel } from '@/components/shared/Panel'
import { fmtInt } from '@/lib/format'
import type { Summary } from '@/lib/types'
import { cn } from '@/lib/utils'

const ROWS: {
  label: string
  get: (s: Summary) => number
  format: (n: number) => string
  better: 'lower' | 'higher' | 'fixed'
}[] = [
  { label: 'Alerts delivered', get: (s) => s.delivered.atc, format: fmtInt, better: 'lower' },
  {
    label: 'Volume reduction',
    get: (s) => s.reduction_pct,
    format: (n) => `${n.toFixed(1)}%`,
    better: 'higher',
  },
  {
    label: 'Critical delivered',
    get: (s) => s.critical.rate,
    format: (n) => `${n.toFixed(0)}%`,
    better: 'fixed',
  },
  {
    label: 'Overnight buzzes',
    get: (s) => s.night_interruptions.atc,
    format: fmtInt,
    better: 'lower',
  },
  {
    label: 'Marketing delivered',
    get: (s) => s.marketing_delivered.atc,
    format: fmtInt,
    better: 'lower',
  },
  {
    label: 'Average fatigue',
    get: (s) => s.avg_fatigue.atc,
    format: (n) => n.toFixed(1),
    better: 'lower',
  },
  { label: 'Daily digests', get: (s) => s.digests, format: fmtInt, better: 'fixed' },
]

export function RunComparison({ previous, current }: { previous?: Summary; current?: Summary }) {
  return (
    <Panel
      title="This run against the one before"
      description={
        previous && current
          ? `${previous.label ?? 'Previous run'} on the left, ${current.label ?? 'current run'} on the right.`
          : 'Run a simulation to compare it with the current one.'
      }
    >
      {!previous || !current ? (
        <p className="text-sm text-ink-muted">
          Change a rule and run the simulation to compare it with the default rules.
        </p>
      ) : (
        <table className="w-full text-sm">
          <caption className="sr-only">Previous run compared with the current run</caption>
          <thead>
            <tr className="text-left text-xs text-ink-faint">
              <th scope="col" className="pb-2 font-normal">
                Measure
              </th>
              <th scope="col" className="pb-2 text-right font-normal">
                Before
              </th>
              <th scope="col" className="pb-2 text-right font-normal">
                Now
              </th>
              <th scope="col" className="pb-2 text-right font-normal">
                Change
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rim">
            {ROWS.map((row) => {
              const a = row.get(previous)
              const b = row.get(current)
              const diff = b - a
              const good =
                row.better === 'lower' ? diff < 0 : row.better === 'higher' ? diff > 0 : false
              const bad =
                row.better === 'lower' ? diff > 0 : row.better === 'higher' ? diff < 0 : false
              return (
                <tr key={row.label}>
                  <th scope="row" className="py-2.5 text-left font-normal text-ink-muted">
                    {row.label}
                  </th>
                  <td className="py-2.5 text-right num text-ink-muted">{row.format(a)}</td>
                  <td className="py-2.5 text-right num text-ink">{row.format(b)}</td>
                  <td
                    className={cn(
                      'py-2.5 text-right num',
                      good && 'text-sent',
                      bad && 'text-delayed',
                      !good && !bad && 'text-ink-faint',
                    )}
                  >
                    {Math.abs(diff) < 0.05
                      ? 'same'
                      : `${diff > 0 ? '+' : '−'}${row.format(Math.abs(diff))}`}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </Panel>
  )
}
