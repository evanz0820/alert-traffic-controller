import { Lock } from 'lucide-react'
import type { ReactNode } from 'react'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { fmtInt } from '@/lib/format'
import { cn } from '@/lib/utils'

/** One rule as a flight-progress strip: order, category bar, name, summary, controls. */
export function RuleStrip({
  order,
  name,
  summary,
  enabled,
  onToggle,
  locked,
  acted,
  children,
}: {
  order: number
  name: string
  summary: string
  enabled: boolean
  onToggle?: (on: boolean) => void
  locked?: boolean
  acted?: number
  children?: ReactNode
}) {
  const id = `rule-${order}`
  return (
    <article
      aria-labelledby={`${id}-name`}
      className={cn(
        'relative flex overflow-hidden rounded-xl border border-rim bg-deck transition-opacity',
        !enabled && 'opacity-60',
      )}
    >
      <div
        aria-hidden="true"
        className={cn(
          'w-1 shrink-0',
          locked ? 'bg-critical' : enabled ? 'bg-sent' : 'bg-rim-strong',
        )}
      />
      <div className="flex w-12 shrink-0 flex-col items-center border-r border-rim pt-5">
        <span className="num text-sm text-ink-faint" aria-label={`Step ${order}`}>
          {String(order).padStart(2, '0')}
        </span>
      </div>
      <div className="min-w-0 flex-1 p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h3 id={`${id}-name`} className="font-medium text-ink">
              {name}
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-ink-muted">{summary}</p>
          </div>
          {locked ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  tabIndex={0}
                  className="flex shrink-0 items-center gap-1.5 rounded-md border border-critical/30 bg-critical/10 px-2 py-1 text-xs text-critical"
                >
                  <Lock className="size-3" aria-hidden="true" /> Always on
                </span>
              </TooltipTrigger>
              <TooltipContent className="max-w-60">
                Critical alerts can never be held back, so this rule can't be turned off or moved.
              </TooltipContent>
            </Tooltip>
          ) : (
            <Switch
              checked={enabled}
              onCheckedChange={onToggle}
              aria-label={`${enabled ? 'Turn off' : 'Turn on'} ${name}`}
              className="mt-0.5 shrink-0"
            />
          )}
        </div>
        {children && enabled && <div className="mt-5 space-y-5">{children}</div>}
        {acted !== undefined && (
          <p className="mt-4 text-xs text-ink-faint">
            Decided <span className="num text-ink-muted">{fmtInt(acted)}</span> alerts in the
            selected run
          </p>
        )}
      </div>
    </article>
  )
}

export function SliderField({
  label,
  value,
  display,
  min,
  max,
  step = 1,
  onChange,
}: {
  label: string
  value: number
  display: string
  min: number
  max: number
  step?: number
  onChange: (v: number) => void
}) {
  return (
    <div>
      <div className="mb-2.5 flex items-baseline justify-between gap-3 text-sm">
        <span className="text-ink-muted">{label}</span>
        <span className="num text-ink">{display}</span>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([v]) => v !== undefined && onChange(v)}
        aria-label={label}
      />
    </div>
  )
}
