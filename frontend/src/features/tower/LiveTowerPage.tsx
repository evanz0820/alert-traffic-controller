import { Pause, Play, RotateCcw } from 'lucide-react'
import { useReducedMotion } from 'motion/react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { ErrorState } from '@/components/shared/ErrorState'
import { OutcomeBadge, RuleBadge } from '@/components/shared/OutcomeBadge'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Slider } from '@/components/ui/slider'
import { EVENT_LABEL, fmtInt } from '@/lib/format'
import { useReplay } from '@/lib/queries'
import { useTheme } from '@/lib/theme'
import type { Outcome, Replay, RuleKey } from '@/lib/types'
import { cn } from '@/lib/utils'
import { INBOUND_Y, laneEndX, LANE_Y, LANES, readPalette, TowerSim, type Lane } from './towerEngine'

/** Simulated seconds per real second. */
const SPEEDS = [
  { label: '15 min/s', value: 900 },
  { label: '1 hr/s', value: 3600 },
  { label: '3 hr/s', value: 3 * 3600 },
  { label: '6 hr/s', value: 6 * 3600 },
  { label: '12 hr/s', value: 12 * 3600 },
  { label: '1 day/s', value: 24 * 3600 },
]

const LANE_LABEL: Record<Lane, string> = {
  sent: 'Sent',
  delayed: 'Delayed',
  batched: 'Batched',
  suppressed: 'Suppressed',
}
const LANE_TEXT: Record<Lane, string> = {
  sent: 'text-sent',
  delayed: 'text-delayed',
  batched: 'text-batched',
  suppressed: 'text-suppressed',
}
const INBOUND_LABEL = ['Critical', 'High', 'Low', 'Marketing']
const PRIORITY_KEYS = ['marketing', 'low', 'high', 'critical'] as const

interface Tick {
  i: number
  t: number
  type: string
  outcome: Outcome
  rule: RuleKey
  priority: (typeof PRIORITY_KEYS)[number]
  customer: number
}

function simClock(start: string, offset: number) {
  return new Date(new Date(start).getTime() + offset * 1000).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/New_York',
    timeZoneName: 'short',
  })
}

function Stage({ replay }: { replay: Replay }) {
  const reduce = useReducedMotion() ?? false
  const { theme } = useTheme()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const sim = useMemo(() => new TowerSim(replay), [replay])
  const [playing, setPlaying] = useState(!reduce)
  const [speed, setSpeed] = useState(2)
  const [view, setView] = useState({ simTime: 0, counts: sim.counts })
  const [ticks, setTicks] = useState<Tick[]>([])
  const [stageWidth, setStageWidth] = useState(1000)
  const pending = useRef<number[]>([])

  const controls = useRef({ playing, speed })
  useEffect(() => {
    controls.current = { playing, speed }
  }, [playing, speed])

  // Animation loop: draws every frame, publishes React state at ~8 Hz.
  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const palette = readPalette(document.documentElement)
    let w = 0
    let h = 0
    const resize = () => {
      const box = wrap.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = box.width
      h = box.height
      setStageWidth(w)
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(wrap)

    let frame = 0
    let last = performance.now()
    let lastPublish = 0
    const loop = (ms: number) => {
      const now = ms / 1000
      const dt = Math.min(0.1, (ms - last) / 1000)
      last = ms
      const { playing: on, speed: s } = controls.current
      if (on) {
        const fresh = sim.advance(dt * SPEEDS[s]!.value, now, !reduce)
        if (fresh.length) pending.current.push(...fresh.slice(-12))
        if (sim.simTime >= sim.duration) setPlaying(false)
      }
      sim.draw(ctx, w, h, reduce ? 0 : now, palette)
      if (ms - lastPublish > 120) {
        lastPublish = ms
        setView({ simTime: sim.simTime, counts: { ...sim.counts } })
        if (pending.current.length) {
          const latest = pending.current.slice(-10).reverse()
          pending.current = []
          setTicks((prev) => {
            const seen = new Set(latest)
            const fresh = latest.map((i) => ({
              i,
              t: replay.t[i]!,
              type: replay.event_types[replay.type[i]!]!,
              outcome: replay.outcomes[replay.outcome[i]!]!,
              rule: replay.rules[replay.rule[i]!]!,
              priority: PRIORITY_KEYS[replay.priority[i]!]!,
              customer: replay.customer[i]!,
            }))
            return [...fresh, ...prev.filter((tick) => !seen.has(tick.i))].slice(0, 10)
          })
        }
      }
      frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
    }
  }, [sim, replay, reduce, theme])

  const seek = (t: number) => {
    sim.seek(t)
    pending.current = []
    setTicks([])
    setView({ simTime: sim.simTime, counts: { ...sim.counts } })
  }

  const decided = LANES.reduce((sum, lane) => sum + view.counts[lane], 0)
  const finished = view.simTime >= sim.duration

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section aria-label="Replay" className="self-start rounded-2xl border border-rim bg-deck">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-4 border-b border-rim px-5 py-4">
          <Button
            size="sm"
            onClick={() => (finished ? (seek(0), setPlaying(true)) : setPlaying((p) => !p))}
            aria-label={
              finished ? 'Replay from the start' : playing ? 'Pause replay' : 'Play replay'
            }
          >
            {finished ? <RotateCcw /> : playing ? <Pause /> : <Play />}
            {finished ? 'Replay' : playing ? 'Pause' : 'Play'}
          </Button>
          <div className="flex min-w-48 flex-1 items-center gap-3">
            <span className="shrink-0 text-xs text-ink-muted">Speed</span>
            <Slider
              value={[speed]}
              min={0}
              max={SPEEDS.length - 1}
              step={1}
              onValueChange={([v]) => v !== undefined && setSpeed(v)}
              aria-label="Replay speed"
              aria-valuetext={SPEEDS[speed]!.label}
              className="max-w-40"
            />
            <span className="w-16 shrink-0 num text-xs text-ink">{SPEEDS[speed]!.label}</span>
          </div>
          <div className="ml-auto num text-sm text-ink" aria-live="off">
            {simClock(replay.start, view.simTime)}
          </div>
        </div>

        <div ref={wrapRef} className="relative h-[340px] sm:h-[460px]">
          <canvas
            ref={canvasRef}
            className="absolute inset-0 size-full"
            role="img"
            aria-label={`Animated replay: ${fmtInt(decided)} of ${fmtInt(sim.total)} alerts decided so far.`}
          />
          {INBOUND_Y.map((y, k) => (
            <span
              key={INBOUND_LABEL[k]}
              className={cn(
                'pointer-events-none absolute left-3 -translate-y-[150%] text-[11px]',
                k === 0 ? 'text-critical' : 'text-ink-faint',
              )}
              style={{ top: `${y * 100}%` }}
            >
              {INBOUND_LABEL[k]}
            </span>
          ))}
          {LANES.map((lane) => (
            <div
              key={lane}
              className="absolute right-3 -translate-y-1/2 text-right sm:right-5"
              style={{ top: `${LANE_Y[lane] * 100}%`, left: `${laneEndX(stageWidth) * 100 + 1}%` }}
            >
              <div className={cn('text-[11px] sm:text-xs', LANE_TEXT[lane])}>
                {LANE_LABEL[lane]}
              </div>
              <div className="num text-sm text-ink sm:text-base">{fmtInt(view.counts[lane])}</div>
            </div>
          ))}
        </div>

        <div className="border-t border-rim px-5 py-4">
          <Slider
            value={[view.simTime]}
            min={0}
            max={sim.duration}
            step={3600}
            onValueChange={([v]) => v !== undefined && seek(v)}
            aria-label="Replay position"
            aria-valuetext={simClock(replay.start, view.simTime)}
          />
          <div className="mt-2 flex justify-between text-xs text-ink-faint">
            <span>{simClock(replay.start, 0).split(',').slice(0, 2).join(',')}</span>
            <span className="num">
              {fmtInt(decided)} of {fmtInt(sim.total)} decided
            </span>
            <span>{simClock(replay.start, sim.duration).split(',').slice(0, 2).join(',')}</span>
          </div>
        </div>
      </section>

      <section aria-label="Latest decisions" className="rounded-2xl border border-rim bg-deck">
        <div className="border-b border-rim px-5 py-4">
          <h2 className="text-base font-semibold text-ink">Latest decisions</h2>
          <p className="mt-0.5 text-xs text-ink-muted">The most recent alerts through the tower.</p>
        </div>
        {ticks.length === 0 ? (
          <p className="px-5 py-8 text-sm text-ink-muted">
            {playing ? 'Waiting for the next alert…' : 'Press Play to start the replay.'}
          </p>
        ) : (
          <ol className="divide-y divide-rim">
            {ticks.map((tick) => (
              <li key={tick.i} className="px-5 py-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={cn(
                      'truncate text-sm',
                      tick.priority === 'critical' ? 'text-critical' : 'text-ink',
                    )}
                  >
                    {EVENT_LABEL[tick.type]}
                  </span>
                  <OutcomeBadge outcome={tick.outcome} priority={tick.priority} />
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-ink-faint">
                  <span className="num">
                    {new Date(new Date(replay.start).getTime() + tick.t * 1000).toLocaleTimeString(
                      'en-US',
                      { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' },
                    )}
                  </span>
                  <span className="num">#{tick.customer}</span>
                  {tick.rule !== 'none' && <RuleBadge rule={tick.rule} className="ml-auto" />}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}

export default function LiveTowerPage() {
  const replay = useReplay()
  return (
    <>
      <PageHeader
        title="Live Tower"
        description="Replay all 30 days. Each dot is one alert request entering the controller on the left and leaving on the right with its outcome. Red dots are critical alerts on their express lane: they never wait."
      />
      {replay.isError ? (
        <ErrorState error={replay.error} onRetry={() => replay.refetch()} />
      ) : replay.data ? (
        <Stage replay={replay.data} />
      ) : (
        <Skeleton className="h-[560px] w-full rounded-2xl" />
      )}
    </>
  )
}
