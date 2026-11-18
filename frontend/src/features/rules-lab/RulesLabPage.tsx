import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, LoaderCircle, Play, RotateCcw, Save } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { CountUp } from '@/components/shared/CountUp'
import { ErrorState } from '@/components/shared/ErrorState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { fmtInt } from '@/lib/format'
import { useRuns, useSummary } from '@/lib/queries'
import { useRun } from '@/lib/run-context'
import type { RuleKey, RulesConfig } from '@/lib/types'
import { cn } from '@/lib/utils'
import { RULE_INFO } from './ruleInfo'
import { RuleStrip, SliderField } from './RuleStrip'
import { RunComparison } from './RunComparison'

type Rules = RulesConfig['rules']
type Toggleable = Exclude<keyof Rules, 'critical_bypass'>

const hourOf = (hhmm: string) => Number(hhmm.split(':')[0])
const asClock = (hour: number) => `${String(hour).padStart(2, '0')}:00`
const clockLabel = (hour: number) => {
  const h = hour % 12 === 0 ? 12 : hour % 12
  return `${h} ${hour < 12 || hour === 24 ? 'AM' : 'PM'}`
}
const asDigestClock = (hour: number) => `${String(hour).padStart(2, '0')}:00`

/** Short human label for what changed, used to name the new run. */
function describeChanges(base: RulesConfig, draft: RulesConfig): string[] {
  const out: string[] = []
  const b = base.rules
  const d = draft.rules
  for (const key of Object.keys(RULE_INFO) as Toggleable[]) {
    if (key in b && 'enabled' in b[key] && b[key].enabled !== d[key].enabled) {
      out.push(`${RULE_INFO[key].name} ${d[key].enabled ? 'on' : 'off'}`)
    }
  }
  const cap = d.frequency_cap
  if (cap.daily_cap !== b.frequency_cap.daily_cap) out.push(`${cap.daily_cap}/day cap`)
  if (cap.hourly_cap !== b.frequency_cap.hourly_cap) out.push(`${cap.hourly_cap}/hour cap`)
  if (cap.marketing_daily_cap !== b.frequency_cap.marketing_daily_cap)
    out.push(`${cap.marketing_daily_cap} offer/day`)
  if (cap.marketing_weekly_cap !== b.frequency_cap.marketing_weekly_cap)
    out.push(`${cap.marketing_weekly_cap} offers/week`)
  const q = d.quiet_hours
  if (q.start !== b.quiet_hours.start || q.end !== b.quiet_hours.end)
    out.push(`quiet ${clockLabel(hourOf(q.start))}–${clockLabel(hourOf(q.end))}`)
  if (q.high_amount_exemption !== b.quiet_hours.high_amount_exemption)
    out.push(`urgent above $${fmtInt(q.high_amount_exemption)}`)
  if (d.fatigue_gate.threshold !== b.fatigue_gate.threshold)
    out.push(`fatigue limit ${d.fatigue_gate.threshold}`)
  if (d.digest.send_at !== b.digest.send_at)
    out.push(`digest at ${clockLabel(hourOf(d.digest.send_at))}`)
  if (d.channel_routing.push_open_window_minutes !== b.channel_routing.push_open_window_minutes)
    out.push(`${d.channel_routing.push_open_window_minutes} min push window`)
  return out
}

function Readout({
  label,
  value,
  format,
  tone,
}: {
  label: string
  value: number
  format: (n: number) => string
  tone?: string
}) {
  return (
    <div className="px-5 py-4">
      <div className="text-[13px] text-ink-muted">{label}</div>
      <CountUp
        value={value}
        format={format}
        className={cn('mt-1.5 block num text-2xl', tone ?? 'text-ink')}
      />
    </div>
  )
}

const asInt = (n: number) => fmtInt(n)
const asPct1 = (n: number) => `${n.toFixed(1)}%`
const asPct0 = (n: number) => `${n.toFixed(0)}%`
const asDec1 = (n: number) => n.toFixed(1)

export default function RulesLabPage() {
  const queryClient = useQueryClient()
  const { runId, setRunId } = useRun()
  const runs = useRuns()
  const summary = useSummary()
  const base = useMemo(() => runs.data?.find((r) => r.id === runId)?.config, [runs.data, runId])

  // Edits belong to the run they were made against; switching runs starts from that run's config.
  const [edits, setEdits] = useState<{ runId: string; config: RulesConfig } | null>(null)
  const [explicitPrevious, setPreviousId] = useState<string>()
  const [saved, setSaved] = useState(false)

  const draft = edits && edits.runId === runId ? edits.config : (base ?? null)
  const setDraft = (update: (d: RulesConfig) => RulesConfig) => {
    if (runId && draft) setEdits({ runId, config: update(draft) })
  }
  const previousId = explicitPrevious ?? runs.data?.find((r) => r.id !== runId)?.id

  const changes = base && draft ? describeChanges(base, draft) : []
  const dirty = changes.length > 0

  const simulate = useMutation({
    mutationFn: (config: RulesConfig) =>
      api.simulate(config, changes.length ? changes.slice(0, 3).join(', ') : 'Rerun'),
    onSuccess: async (result) => {
      setPreviousId(runId)
      await queryClient.invalidateQueries({ queryKey: ['runs'] })
      setRunId(result.run_id)
    },
  })

  const save = useMutation({
    mutationFn: (config: RulesConfig) => api.saveConfig(config),
    onSuccess: () => {
      setSaved(true)
      queryClient.invalidateQueries({ queryKey: ['config'] })
      setTimeout(() => setSaved(false), 2500)
    },
  })

  if (runs.isError) return <ErrorState error={runs.error} onRetry={() => runs.refetch()} />
  if (!draft || !summary.data) {
    return (
      <div aria-busy="true" aria-label="Loading rules">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="mt-8 h-24 w-full rounded-2xl" />
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  const rules = draft.rules
  const s = summary.data
  const set = <K extends keyof Rules>(key: K, patch: Partial<Rules[K]>) =>
    setDraft((d) => ({ ...d, rules: { ...d.rules, [key]: { ...d.rules[key], ...patch } } }))
  const acted = (key: RuleKey) => s.by_rule[key] ?? 0

  const runButton = (
    <Button onClick={() => simulate.mutate(draft)} disabled={simulate.isPending}>
      {simulate.isPending ? <LoaderCircle className="animate-spin" /> : <Play />}
      {simulate.isPending ? 'Running…' : 'Run simulation'}
    </Button>
  )

  const strips: Record<Exclude<RuleKey, 'none'>, (order: number) => ReactNode> = {
    critical_bypass: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.critical_bypass.name}
        summary={RULE_INFO.critical_bypass.summary}
        enabled
        locked
        acted={acted('critical_bypass')}
      />
    ),
    dedup: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.dedup.name}
        summary={RULE_INFO.dedup.summary}
        enabled={rules.dedup.enabled}
        onToggle={(enabled) => set('dedup', { enabled })}
        acted={acted('dedup')}
      />
    ),
    preference_filter: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.preference_filter.name}
        summary={RULE_INFO.preference_filter.summary}
        enabled={rules.preference_filter.enabled}
        onToggle={(enabled) => set('preference_filter', { enabled })}
        acted={acted('preference_filter')}
      />
    ),
    fatigue_gate: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.fatigue_gate.name}
        summary={RULE_INFO.fatigue_gate.summary}
        enabled={rules.fatigue_gate.enabled}
        onToggle={(enabled) => set('fatigue_gate', { enabled })}
        acted={acted('fatigue_gate')}
      >
        <SliderField
          label="Pause marketing above this score"
          value={rules.fatigue_gate.threshold}
          display={`${rules.fatigue_gate.threshold} / 100`}
          min={10}
          max={100}
          step={5}
          onChange={(threshold) => set('fatigue_gate', { threshold })}
        />
      </RuleStrip>
    ),
    quiet_hours: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.quiet_hours.name}
        summary={RULE_INFO.quiet_hours.summary}
        enabled={rules.quiet_hours.enabled}
        onToggle={(enabled) => set('quiet_hours', { enabled })}
        acted={acted('quiet_hours')}
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <SliderField
            label="Quiet from"
            value={hourOf(rules.quiet_hours.start)}
            display={clockLabel(hourOf(rules.quiet_hours.start))}
            min={19}
            max={23}
            onChange={(h) => set('quiet_hours', { start: asClock(h) })}
          />
          <SliderField
            label="Until"
            value={hourOf(rules.quiet_hours.end)}
            display={clockLabel(hourOf(rules.quiet_hours.end))}
            min={5}
            max={10}
            onChange={(h) => set('quiet_hours', { end: asClock(h) })}
          />
        </div>
        <SliderField
          label="Send anyway when a transaction is at least"
          value={rules.quiet_hours.high_amount_exemption}
          display={`$${fmtInt(rules.quiet_hours.high_amount_exemption)}`}
          min={500}
          max={10000}
          step={250}
          onChange={(v) => set('quiet_hours', { high_amount_exemption: v })}
        />
      </RuleStrip>
    ),
    frequency_cap: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.frequency_cap.name}
        summary={RULE_INFO.frequency_cap.summary}
        enabled={rules.frequency_cap.enabled}
        onToggle={(enabled) => set('frequency_cap', { enabled })}
        acted={acted('frequency_cap')}
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <SliderField
            label="Alerts per day"
            value={rules.frequency_cap.daily_cap}
            display={String(rules.frequency_cap.daily_cap)}
            min={1}
            max={15}
            onChange={(v) => set('frequency_cap', { daily_cap: v })}
          />
          <SliderField
            label="Alerts per hour"
            value={rules.frequency_cap.hourly_cap}
            display={String(rules.frequency_cap.hourly_cap)}
            min={1}
            max={6}
            onChange={(v) => set('frequency_cap', { hourly_cap: v })}
          />
          <SliderField
            label="Marketing offers per day"
            value={rules.frequency_cap.marketing_daily_cap}
            display={String(rules.frequency_cap.marketing_daily_cap)}
            min={0}
            max={3}
            onChange={(v) => set('frequency_cap', { marketing_daily_cap: v })}
          />
          <SliderField
            label="Marketing offers per week"
            value={rules.frequency_cap.marketing_weekly_cap}
            display={String(rules.frequency_cap.marketing_weekly_cap)}
            min={0}
            max={7}
            onChange={(v) => set('frequency_cap', { marketing_weekly_cap: v })}
          />
        </div>
      </RuleStrip>
    ),
    digest: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.digest.name}
        summary={RULE_INFO.digest.summary}
        enabled={rules.digest.enabled}
        onToggle={(enabled) => set('digest', { enabled })}
        acted={acted('digest')}
      >
        <SliderField
          label="Send the digest at"
          value={hourOf(rules.digest.send_at)}
          display={clockLabel(hourOf(rules.digest.send_at))}
          min={6}
          max={21}
          onChange={(h) => set('digest', { send_at: asDigestClock(h) })}
        />
      </RuleStrip>
    ),
    channel_routing: (order) => (
      <RuleStrip
        order={order}
        name={RULE_INFO.channel_routing.name}
        summary={RULE_INFO.channel_routing.summary}
        enabled={rules.channel_routing.enabled}
        onToggle={(enabled) => set('channel_routing', { enabled })}
        acted={acted('channel_routing')}
      >
        <SliderField
          label="Follow up by email if a push is unread after"
          value={rules.channel_routing.push_open_window_minutes}
          display={`${rules.channel_routing.push_open_window_minutes} min`}
          min={5}
          max={120}
          step={5}
          onChange={(v) => set('channel_routing', { push_open_window_minutes: v })}
        />
      </RuleStrip>
    ),
  }

  return (
    <>
      <PageHeader
        title="Rules Lab"
        description="Every alert passes through these rules in order. Change a setting, run the simulation over the same 30 days, and compare the result."
        actions={runButton}
      />

      <section
        aria-label="Results of the selected run"
        aria-live="polite"
        className="grid grid-cols-2 overflow-hidden rounded-2xl border border-rim bg-deck sm:grid-cols-4 [&>*]:border-rim sm:[&>*:not(:last-child)]:border-r max-sm:[&>*:nth-child(-n+2)]:border-b max-sm:[&>*:nth-child(odd)]:border-r"
      >
        <Readout label="Alerts delivered" value={s.delivered.atc} format={asInt} />
        <Readout
          label="Volume reduction"
          value={s.reduction_pct}
          format={asPct1}
          tone="text-sent"
        />
        <Readout
          label="Critical delivered"
          value={s.critical.rate}
          format={asPct0}
          tone="text-critical"
        />
        <Readout label="Average fatigue" value={s.avg_fatigue.atc} format={asDec1} />
      </section>

      {simulate.isError && (
        <p role="alert" className="mt-4 text-sm text-delayed">
          The simulation didn't run: {(simulate.error as Error).message}
        </p>
      )}

      <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1fr)_400px]">
        <ol className="grid content-start gap-4 lg:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
          {draft.pipeline.map((key, i) => (
            <li key={key} className="[&>article]:h-full">
              {strips[key as Exclude<RuleKey, 'none'>]?.(i + 1)}
            </li>
          ))}
        </ol>

        <aside className="space-y-6 xl:sticky xl:top-10 xl:self-start">
          <RunComparison previousId={previousId} currentId={runId} />
          <div className="rounded-2xl border border-rim bg-deck p-5 text-sm">
            <p className="text-ink">
              {dirty ? (
                <>
                  <span className="num">{changes.length}</span> unsaved change
                  {changes.length === 1 ? '' : 's'}: {changes.join(', ')}.
                </>
              ) : (
                'These settings match the selected run.'
              )}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {runButton}
              <Button variant="outline" onClick={() => setEdits(null)} disabled={!dirty}>
                <RotateCcw /> Revert
              </Button>
              <Button variant="ghost" onClick={() => save.mutate(draft)} disabled={save.isPending}>
                {saved ? <Check /> : <Save />}
                {saved ? 'Saved' : 'Save as default'}
              </Button>
            </div>
            <p className="mt-3 text-xs text-ink-faint">
              Saving writes these settings to rules.yaml, so new runs start from them.
            </p>
          </div>
        </aside>
      </div>
    </>
  )
}
