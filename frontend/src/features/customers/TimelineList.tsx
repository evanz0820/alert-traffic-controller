import { Inbox } from 'lucide-react'
import { OutcomeBadge, RuleBadge } from '@/components/shared/OutcomeBadge'
import { EVENT_LABEL } from '@/lib/format'
import type { TimelineItem } from '@/lib/types'
import { cn } from '@/lib/utils'

function when(item: TimelineItem) {
  return item.delivered_at ?? item.requested_at!
}

function dayKey(iso: string, tz: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: tz,
  })
}

function clock(iso: string, tz: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: tz,
  })
}

function Entry({
  item,
  tz,
  showDecision,
}: {
  item: TimelineItem
  tz: string
  showDecision: boolean
}) {
  const suppressed = item.outcome === 'SUPPRESSED'
  const title =
    item.kind === 'digest'
      ? 'Daily digest'
      : (EVENT_LABEL[item.event_type ?? ''] ?? item.event_type)
  const moved =
    item.delivered_at &&
    item.requested_at &&
    item.delivered_at.slice(0, 16) !== item.requested_at.slice(0, 16)
  return (
    <li className="grid grid-cols-[64px_minmax(0,1fr)] gap-3 py-3">
      <div className="pt-0.5 num text-xs text-ink-faint">
        <div className={cn(suppressed && 'line-through')}>{clock(when(item), tz)}</div>
        {moved && item.outcome === 'DELAYED' && (
          <div className="mt-0.5 text-[11px]">asked {clock(item.requested_at!, tz)}</div>
        )}
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              'text-sm font-medium',
              item.priority === 'critical' ? 'text-critical' : 'text-ink',
              suppressed && 'text-ink-faint',
            )}
          >
            {title}
          </span>
          {showDecision && <OutcomeBadge outcome={item.outcome} priority={item.priority} />}
          {item.channels.length > 0 && (
            <span className="text-xs text-ink-faint">via {item.channels.join(' + ')}</span>
          )}
        </div>
        <p
          className={cn(
            'mt-1.5 rounded-lg border border-rim bg-console px-3 py-2 text-[13px] leading-relaxed text-ink-muted',
            suppressed && 'border-dashed bg-transparent opacity-70',
          )}
        >
          {item.kind === 'digest' && <Inbox className="mr-1.5 inline size-3.5 align-[-2px]" />}
          {item.preview}
        </p>
        {showDecision && item.rule !== 'none' && (
          <div className="mt-1.5 flex flex-wrap items-start gap-2 text-xs text-ink-muted">
            <RuleBadge rule={item.rule} />
            <span className="min-w-0 flex-1 pt-0.5">{item.explanation}</span>
          </div>
        )}
      </div>
    </li>
  )
}

export function TimelineList({
  items,
  tz,
  showDecision,
}: {
  items: TimelineItem[]
  tz: string
  showDecision: boolean
}) {
  const days = new Map<string, TimelineItem[]>()
  for (const item of items) {
    const key = dayKey(when(item), tz)
    days.set(key, [...(days.get(key) ?? []), item])
  }
  return (
    <div className="space-y-4">
      {[...days.entries()].map(([day, entries]) => (
        <section key={day} aria-label={day}>
          <h4 className="sticky top-0 z-10 -mx-1 bg-deck/95 px-1 py-1.5 text-xs font-medium text-ink-faint backdrop-blur">
            {day}
          </h4>
          <ul className="divide-y divide-rim">
            {entries.map((item, i) => (
              <Entry
                key={item.alert_id ?? `digest-${day}-${i}`}
                item={item}
                tz={tz}
                showDecision={showDecision}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
