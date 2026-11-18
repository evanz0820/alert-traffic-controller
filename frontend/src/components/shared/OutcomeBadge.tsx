import { OUTCOME_LABEL, OUTCOME_TONE, RULE_LABEL } from '@/lib/format'
import type { Outcome, Priority, RuleKey } from '@/lib/types'
import { cn } from '@/lib/utils'

const TONE_CLASS = {
  sent: 'text-sent bg-sent/10 ring-sent/25',
  delayed: 'text-delayed bg-delayed/10 ring-delayed/25',
  batched: 'text-batched bg-batched/10 ring-batched/25',
  suppressed: 'text-suppressed bg-suppressed/10 ring-suppressed/25',
  critical: 'text-critical bg-critical/10 ring-critical/30',
} as const

/** Outcome chip: color plus a distinct glyph so state never relies on color alone. */
const GLYPH: Record<Outcome, string> = {
  SENT: '●',
  REROUTED: '↪',
  DELAYED: '◐',
  BATCHED_TO_DIGEST: '▤',
  SUPPRESSED: '○',
}

export function OutcomeBadge({
  outcome,
  priority,
  className,
}: {
  outcome: Outcome
  priority?: Priority | null
  className?: string
}) {
  const tone = priority === 'critical' ? 'critical' : OUTCOME_TONE[outcome]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset',
        TONE_CLASS[tone],
        className,
      )}
    >
      <span aria-hidden="true" className="text-[10px] leading-none">
        {GLYPH[outcome]}
      </span>
      {OUTCOME_LABEL[outcome]}
    </span>
  )
}

export function RuleBadge({ rule, className }: { rule: RuleKey; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border border-rim bg-console px-2 py-0.5 text-xs whitespace-nowrap text-ink-muted',
        className,
      )}
    >
      {RULE_LABEL[rule]}
    </span>
  )
}

export function PriorityDot({ priority }: { priority: Priority }) {
  const cls = {
    critical: 'bg-critical',
    high: 'bg-ink',
    low: 'bg-ink-faint',
    marketing: 'border border-ink-faint bg-transparent',
  }[priority]
  return (
    <span aria-hidden="true" className={cn('inline-block size-2 shrink-0 rounded-full', cls)} />
  )
}
