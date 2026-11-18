import { fmtInt } from '@/lib/format'
import type { Flows } from '@/lib/types'

/** Plain-language description of the Sankey for screen readers and skimmers. */
export function describeFlows(flows: Flows): string[] {
  const kind = (i: number) => flows.nodes[i]?.kind
  const total = flows.links
    .filter((l) => kind(l.source) === 'event')
    .reduce((s, l) => s + l.value, 0)
  const byRule = flows.links
    .filter((l) => kind(l.source) === 'event')
    .reduce<Map<number, number>>(
      (m, l) => m.set(l.target, (m.get(l.target) ?? 0) + l.value),
      new Map(),
    )
  const byOutcome = flows.links
    .filter((l) => kind(l.source) === 'rule')
    .reduce<Map<number, number>>(
      (m, l) => m.set(l.target, (m.get(l.target) ?? 0) + l.value),
      new Map(),
    )

  const pct = (n: number) => `${((100 * n) / total).toFixed(0)}%`
  const topRules = [...byRule.entries()]
    .filter(([i]) => flows.nodes[i]?.key !== 'none')
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([i, v]) => `${flows.nodes[i]!.name.toLowerCase()} (${fmtInt(v)}, ${pct(v)})`)
  const outcomes = [...byOutcome.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([i, v]) => `${flows.nodes[i]!.name.toLowerCase()} ${pct(v)}`)
  const critical = flows.nodes.findIndex((n) => n.key === 'critical_bypass')
  const criticalCount = critical >= 0 ? (byRule.get(critical) ?? 0) : 0

  return [
    `${fmtInt(total)} alert requests flow from 12 upstream event types through the rule pipeline.`,
    `The rules that act most often are ${topRules.join(', ')}.`,
    `Final outcomes: ${outcomes.join(', ')}.`,
    `All ${fmtInt(criticalCount)} critical alerts take the critical bypass straight to sent.`,
  ]
}
