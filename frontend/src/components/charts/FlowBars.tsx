import { fmtInt, fmtPct } from '@/lib/format'
import type { Flows } from '@/lib/types'
import { cn } from '@/lib/utils'

const TONE: Record<string, string> = {
  SENT: 'bg-sent',
  REROUTED: 'bg-sent/60',
  DELAYED: 'bg-delayed',
  BATCHED_TO_DIGEST: 'bg-batched',
  SUPPRESSED: 'bg-suppressed',
}

const LEGEND = [
  ['bg-sent', 'Sent'],
  ['bg-sent/60', 'Rerouted'],
  ['bg-delayed', 'Delayed'],
  ['bg-batched', 'Batched'],
  ['bg-suppressed', 'Suppressed'],
  ['bg-critical', 'Critical'],
] as const

/** Compact alternative to the Sankey for narrow screens: one stacked bar per deciding rule. */
export function FlowBars({ data }: { data: Flows }) {
  const rules = data.nodes
    .map((node, index) => ({ node, index }))
    .filter(({ node }) => node.kind === 'rule')
  const total = data.links
    .filter((l) => data.nodes[l.source]?.kind === 'event')
    .reduce((sum, l) => sum + l.value, 0)

  const rows = rules
    .map(({ node, index }) => {
      const parts = data.links
        .filter((l) => l.source === index)
        .map((l) => ({ outcome: data.nodes[l.target]!, value: l.value }))
      return { node, parts, value: parts.reduce((s, p) => s + p.value, 0) }
    })
    .sort((a, b) => b.value - a.value)

  return (
    <>
      <ul
        aria-hidden="true"
        className="mb-5 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-muted"
      >
        {LEGEND.map(([tone, label]) => (
          <li key={label} className="flex items-center gap-1.5">
            <span className={cn('size-2 rounded-full', tone)} />
            {label}
          </li>
        ))}
      </ul>
      <ul className="space-y-4">
        {rows.map(({ node, parts, value }) => (
          <li key={node.key}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className={cn('text-ink', node.key === 'critical_bypass' && 'text-critical')}>
                {node.name}
              </span>
              <span className="num text-ink-muted">
                {fmtInt(value)}{' '}
                <span className="text-ink-faint">{fmtPct((100 * value) / total, 1)}</span>
              </span>
            </div>
            <div className="mt-1.5 flex h-2 overflow-hidden rounded-full bg-console">
              {parts.map((p) => (
                <div
                  key={p.outcome.key}
                  title={`${p.outcome.name}: ${fmtInt(p.value)}`}
                  className={cn(
                    node.key === 'critical_bypass' ? 'bg-critical' : TONE[p.outcome.key],
                  )}
                  style={{ width: `${(100 * p.value) / value}%` }}
                />
              ))}
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}
