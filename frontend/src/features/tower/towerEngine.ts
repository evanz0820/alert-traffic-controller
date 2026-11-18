import type { Replay } from '@/lib/types'

/** Exit lanes, top to bottom. Rerouted alerts are delivered, so they share the Sent lane. */
export const LANES = ['sent', 'delayed', 'batched', 'suppressed'] as const
export type Lane = (typeof LANES)[number]

/** Inbound lanes by priority index (3 critical ... 0 marketing), top to bottom. */
export const INBOUND = [3, 2, 1, 0] as const

const OUTCOME_LANE: Record<string, Lane> = {
  SENT: 'sent',
  REROUTED: 'sent',
  DELAYED: 'delayed',
  BATCHED_TO_DIGEST: 'batched',
  SUPPRESSED: 'suppressed',
}

export const INBOUND_Y = [0.14, 0.38, 0.62, 0.86]
export const LANE_Y: Record<Lane, number> = {
  sent: 0.16,
  delayed: 0.39,
  batched: 0.62,
  suppressed: 0.85,
}
export const TOWER_X = 0.46
/** Where exit lanes end (fraction of width); narrow stages leave more room for labels. */
export const laneEndX = (width: number) => (width < 560 ? 0.72 : 0.86)

const MAX_PARTICLES = 1600
const TRAVEL = 1.5 // seconds of wall time a dot spends crossing the stage

export interface Palette {
  critical: string
  high: string
  low: string
  marketing: string
  sent: string
  delayed: string
  batched: string
  suppressed: string
  rim: string
  ink: string
}

/** Pooled particle storage in typed arrays: no per-frame allocation. */
export class TowerSim {
  readonly replay: Replay
  readonly laneOf: Uint8Array
  readonly total: number
  index = 0
  simTime = 0
  counts: Record<Lane, number> = { sent: 0, delayed: 0, batched: 0, suppressed: 0 }

  private born = new Float32Array(MAX_PARTICLES)
  private jitter = new Float32Array(MAX_PARTICLES)
  private prio = new Uint8Array(MAX_PARTICLES)
  private lane = new Uint8Array(MAX_PARTICLES)
  private live = new Uint8Array(MAX_PARTICLES)
  private cursor = 0

  constructor(replay: Replay) {
    this.replay = replay
    this.total = replay.t.length
    this.laneOf = new Uint8Array(this.total)
    for (let i = 0; i < this.total; i++) {
      const outcome = replay.outcomes[replay.outcome[i]!]!
      this.laneOf[i] = LANES.indexOf(OUTCOME_LANE[outcome]!)
    }
  }

  get duration() {
    return this.replay.t[this.total - 1] ?? 0
  }

  /** Jump to a sim time: recount everything before it and clear in-flight dots. */
  seek(simTime: number) {
    this.simTime = Math.max(0, Math.min(simTime, this.duration))
    this.counts = { sent: 0, delayed: 0, batched: 0, suppressed: 0 }
    let i = 0
    while (i < this.total && this.replay.t[i]! <= this.simTime) {
      this.counts[LANES[this.laneOf[i]!]!]++
      i++
    }
    this.index = i
    this.live.fill(0)
  }

  /** Advance sim time; returns indices of newly decided alerts (for the ticker). */
  advance(simDelta: number, now: number, spawn: boolean): number[] {
    this.simTime = Math.min(this.simTime + simDelta, this.duration)
    const fresh: number[] = []
    while (this.index < this.total && this.replay.t[this.index]! <= this.simTime) {
      const i = this.index++
      const lane = this.laneOf[i]!
      this.counts[LANES[lane]!]++
      fresh.push(i)
      if (spawn) this.spawn(i, lane, now)
    }
    return fresh
  }

  private spawn(i: number, lane: number, now: number) {
    const slot = this.cursor
    this.cursor = (this.cursor + 1) % MAX_PARTICLES
    this.born[slot] = now
    this.jitter[slot] = ((i * 2654435761) % 1000) / 1000 - 0.5
    this.prio[slot] = this.replay.priority[i]!
    this.lane[slot] = lane
    this.live[slot] = 1
  }

  draw(ctx: CanvasRenderingContext2D, w: number, h: number, now: number, palette: Palette) {
    ctx.clearRect(0, 0, w, h)
    const cx = w * TOWER_X
    const cy = h / 2
    const r = Math.min(h * 0.2, 86)
    const left = 12
    const end = w * laneEndX(w)

    // Lanes
    ctx.lineWidth = 1
    ctx.strokeStyle = palette.rim
    ctx.setLineDash([3, 5])
    for (const y of INBOUND_Y) {
      ctx.beginPath()
      ctx.moveTo(left, y * h)
      ctx.quadraticCurveTo(cx - r * 1.6, y * h, cx - r, cy + (y - 0.5) * r * 0.9)
      ctx.stroke()
    }
    for (const lane of LANES) {
      const y = LANE_Y[lane] * h
      ctx.beginPath()
      ctx.moveTo(cx + r, cy + (LANE_Y[lane] - 0.5) * r * 0.9)
      ctx.quadraticCurveTo(cx + r * 1.8, y, end, y)
      ctx.stroke()
    }
    ctx.setLineDash([])

    // Radar scope
    ctx.strokeStyle = palette.rim
    for (const k of [1, 0.66, 0.33]) {
      ctx.beginPath()
      ctx.arc(cx, cy, r * k, 0, Math.PI * 2)
      ctx.stroke()
    }
    const sweep = (now * 0.9) % (Math.PI * 2)
    const grad = ctx.createConicGradient?.(sweep - 0.9, cx, cy)
    if (grad) {
      grad.addColorStop(0, 'transparent')
      grad.addColorStop(0.14, `${palette.sent}55`)
      grad.addColorStop(0.145, 'transparent')
      ctx.fillStyle = grad
      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.fill()
    }
    // Tower glyph
    ctx.fillStyle = palette.low
    const s = r / 62
    ctx.fillRect(cx - 9 * s, cy - 15 * s, 18 * s, 7 * s)
    ctx.beginPath()
    ctx.moveTo(cx - 4 * s, cy - 8 * s)
    ctx.lineTo(cx + 4 * s, cy - 8 * s)
    ctx.lineTo(cx + 6 * s, cy + 14 * s)
    ctx.lineTo(cx - 6 * s, cy + 14 * s)
    ctx.closePath()
    ctx.fill()

    // Particles
    const laneColor = [palette.sent, palette.delayed, palette.batched, palette.suppressed]
    const inColor = [palette.marketing, palette.low, palette.high, palette.critical]
    for (let p = 0; p < MAX_PARTICLES; p++) {
      if (!this.live[p]) continue
      const age = (now - this.born[p]!) / TRAVEL
      if (age >= 1) {
        this.live[p] = 0
        continue
      }
      const prio = this.prio[p]!
      const lane = this.lane[p]!
      const jit = this.jitter[p]! * 14
      const y0 = INBOUND_Y[3 - prio]! * h + jit
      const laneY = LANE_Y[LANES[lane]!] * h + jit * 0.6
      let x: number
      let y: number
      let color: string
      let alpha = 1
      if (prio === 3) {
        // Critical express lane: over the tower, straight to Sent, never held.
        const t = Math.min(1, age * 1.5)
        x = left + (end - left) * t
        const arc = Math.sin(t * Math.PI) * h * 0.08
        y = y0 + (laneY - y0) * t - arc
        color = palette.critical
        if (t >= 1) alpha = Math.max(0, 1 - (age * 1.5 - 1) * 3)
      } else if (age < 0.5) {
        const t = age / 0.5
        const ty = cy + (y0 / h - 0.5) * r * 0.9
        x = quad(left, cx - r * 1.6, cx - r * 0.2, t)
        y = quad(y0, y0, ty, t)
        color = inColor[prio]!
      } else {
        const t = (age - 0.5) / 0.5
        const sy = cy + (laneY / h - 0.5) * r * 0.9
        x = quad(cx + r * 0.2, cx + r * 1.8, end, t)
        y = quad(sy, laneY, laneY, t)
        color = laneColor[lane]!
        if (LANES[lane] === 'suppressed') alpha = Math.max(0, 1 - t * 1.4)
      }
      ctx.globalAlpha = alpha
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(x, y, prio === 3 ? 3.2 : 2.2, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }
}

function quad(a: number, b: number, c: number, t: number) {
  const u = 1 - t
  return u * u * a + 2 * u * t * b + t * t * c
}

export function readPalette(el: HTMLElement): Palette {
  const css = getComputedStyle(el)
  const v = (name: string) => css.getPropertyValue(name).trim()
  return {
    critical: v('--critical'),
    high: v('--ink'),
    low: v('--ink-muted'),
    marketing: v('--ink-faint'),
    sent: v('--sent'),
    delayed: v('--delayed'),
    batched: v('--batched'),
    suppressed: v('--suppressed'),
    rim: v('--rim-strong'),
    ink: v('--ink'),
  }
}
