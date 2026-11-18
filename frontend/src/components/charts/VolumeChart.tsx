import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtDay, fmtInt } from '@/lib/format'
import type { DayPoint } from '@/lib/types'

interface TooltipProps {
  active?: boolean
  payload?: { payload: DayPoint }[]
}

function VolumeTooltip({ active, payload }: TooltipProps) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  const cut = point.baseline ? Math.round(100 * (1 - point.atc / point.baseline)) : 0
  return (
    <div className="rounded-lg border border-rim-strong bg-console px-3 py-2 text-xs shadow-lg shadow-black/20">
      <div className="font-medium text-ink">{fmtDay(point.date)}</div>
      <dl className="mt-1.5 grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5">
        <dt className="text-ink-muted">Without ATC</dt>
        <dd className="text-right num text-ink">{fmtInt(point.baseline)}</dd>
        <dt className="text-ink-muted">With ATC</dt>
        <dd className="text-right num text-sent">{fmtInt(point.atc)}</dd>
        <dt className="text-ink-muted">Critical sent</dt>
        <dd className="text-right num text-critical">{fmtInt(point.critical)}</dd>
      </dl>
      <div className="mt-1.5 text-ink-faint">{cut}% fewer alerts that day</div>
    </div>
  )
}

export function VolumeChart({ data }: { data: DayPoint[] }) {
  return (
    <div className="relative min-h-[280px] flex-1">
      <ResponsiveContainer width="100%" height="100%" className="absolute inset-0">
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
          <defs>
            <linearGradient id="atc-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="var(--sent)" stopOpacity={0.28} />
              <stop offset="1" stopColor="var(--sent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--rim)" />
          <XAxis
            dataKey="date"
            tickFormatter={fmtDay}
            tick={{ fill: 'var(--ink-faint)', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: 'var(--rim)' }}
            minTickGap={28}
          />
          <YAxis
            tick={{ fill: 'var(--ink-faint)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip content={<VolumeTooltip />} cursor={{ stroke: 'var(--rim-strong)' }} />
          <Line
            type="monotone"
            dataKey="baseline"
            name="Without ATC"
            stroke="var(--baseline)"
            strokeWidth={1.75}
            strokeDasharray="5 4"
            dot={false}
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="atc"
            name="With ATC"
            stroke="var(--sent)"
            strokeWidth={2}
            fill="url(#atc-fill)"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="critical"
            name="Critical sent"
            stroke="var(--critical)"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
