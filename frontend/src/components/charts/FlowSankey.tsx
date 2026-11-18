import { useMemo, useRef, useState, type MouseEvent } from 'react'
import { ResponsiveContainer, Sankey } from 'recharts'
import type { LinkProps, NodeProps } from 'recharts/types/chart/Sankey'
import { fmtInt } from '@/lib/format'
import type { FlowNode, Flows } from '@/lib/types'

const CRITICAL_EVENTS = new Set(['fraud_suspected', 'card_locked', 'new_device_login'])

const OUTCOME_COLOR: Record<string, string> = {
  SENT: 'var(--sent)',
  REROUTED: 'var(--sent)',
  DELAYED: 'var(--delayed)',
  BATCHED_TO_DIGEST: 'var(--batched)',
  SUPPRESSED: 'var(--suppressed)',
}

type Node = FlowNode & { value?: number }
interface Hover {
  x: number
  y: number
  source: Node
  target: Node
  value: number
  share: number
  maxLeft: number
}

/** The color a band carries: the outcome it ends in, or red for critical traffic. */
function bandColor(source: Node, target: Node) {
  if (source.key === 'critical_bypass' || CRITICAL_EVENTS.has(source.key)) return 'var(--critical)'
  if (target.kind === 'outcome') return OUTCOME_COLOR[target.key] ?? 'var(--baseline)'
  return 'var(--baseline)'
}

function nodeColor(node: Node) {
  if (node.kind === 'outcome') return OUTCOME_COLOR[node.key] ?? 'var(--baseline)'
  if (node.key === 'critical_bypass' || CRITICAL_EVENTS.has(node.key)) return 'var(--critical)'
  return node.kind === 'rule' ? 'var(--ink-muted)' : 'var(--baseline)'
}

export function FlowSankey({ data, height = 600 }: { data: Flows; height?: number }) {
  const wrap = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<Hover | null>(null)

  const outTotals = useMemo(() => {
    const totals = new Map<number, number>()
    for (const l of data.links) totals.set(l.source, (totals.get(l.source) ?? 0) + l.value)
    return totals
  }, [data])

  const chartData = useMemo(
    () => ({ nodes: data.nodes.map((n) => ({ ...n })), links: data.links.map((l) => ({ ...l })) }),
    [data],
  )

  const track = (e: MouseEvent, link: LinkProps) => {
    const box = wrap.current?.getBoundingClientRect()
    if (!box) return
    const source = link.payload.source as unknown as Node & { index?: number }
    const target = link.payload.target as unknown as Node
    const sourceIndex = data.nodes.findIndex((n) => n.key === source.key && n.kind === source.kind)
    const value = link.payload.value
    setHover({
      x: e.clientX - box.left,
      y: e.clientY - box.top,
      source,
      target,
      value,
      share: value / (outTotals.get(sourceIndex) ?? value),
      maxLeft: box.width - 260,
    })
  }

  const renderLink = (props: LinkProps) => {
    const {
      sourceX,
      targetX,
      sourceY,
      targetY,
      sourceControlX,
      targetControlX,
      linkWidth,
      index,
      payload,
    } = props
    const source = payload.source as unknown as Node
    const target = payload.target as unknown as Node
    const active = hover && hover.source.key === source.key && hover.target.key === target.key
    const dimmed = hover && !active
    return (
      <path
        key={`link-${index}`}
        d={`M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`}
        fill="none"
        stroke={bandColor(source, target)}
        strokeWidth={Math.max(1, linkWidth)}
        strokeOpacity={active ? 0.6 : dimmed ? 0.08 : 0.24}
        style={{ transition: 'stroke-opacity 120ms ease-out', cursor: 'pointer' }}
        onMouseEnter={(e) => track(e, props)}
        onMouseMove={(e) => track(e, props)}
        onMouseLeave={() => setHover(null)}
      />
    )
  }

  const renderNode = ({ x, y, width, height: h, payload, index }: NodeProps) => {
    const node = payload as unknown as Node
    const value = (payload as { value?: number }).value ?? 0
    const color = nodeColor(node)
    const left = node.kind === 'event'
    const right = node.kind === 'outcome'
    const tx = left ? x - 10 : x + width + 10
    const anchor = left ? 'end' : 'start'
    const cy = y + h / 2
    return (
      <g key={`node-${index}`}>
        <rect x={x} y={y} width={width} height={Math.max(2, h)} rx={2} fill={color} />
        <text
          x={tx}
          y={cy}
          textAnchor={anchor}
          dominantBaseline="middle"
          className="fill-ink text-[12.5px]"
          paintOrder="stroke"
          stroke={node.kind === 'rule' ? 'var(--deck)' : 'none'}
          strokeWidth={node.kind === 'rule' ? 4 : 0}
          strokeLinejoin="round"
          fontWeight={right || node.kind === 'rule' ? 500 : 400}
        >
          {node.name}
          <tspan className="fill-ink-faint num text-[11.5px]" dx={6}>
            {fmtInt(value)}
          </tspan>
        </text>
      </g>
    )
  }

  return (
    <div ref={wrap} className="relative" onMouseLeave={() => setHover(null)}>
      <ResponsiveContainer width="100%" height={height}>
        <Sankey
          data={chartData}
          node={renderNode}
          link={renderLink}
          nodePadding={16}
          nodeWidth={8}
          iterations={64}
          linkCurvature={0.45}
          margin={{ top: 8, bottom: 8, left: 168, right: 172 }}
          sort
        />
      </ResponsiveContainer>
      {hover && (
        <div
          role="status"
          className="pointer-events-none absolute z-10 w-max max-w-64 rounded-lg border border-rim-strong bg-console px-3 py-2 text-xs shadow-lg shadow-black/20"
          style={{
            left: Math.min(hover.x + 14, hover.maxLeft),
            top: hover.y + 14,
          }}
        >
          <div className="font-medium text-ink">
            {hover.source.name} <span className="text-ink-faint">to</span> {hover.target.name}
          </div>
          <div className="mt-1 text-ink-muted">
            <span className="num text-ink">{fmtInt(hover.value)}</span> alerts,{' '}
            <span className="num text-ink">{(hover.share * 100).toFixed(1)}%</span> of{' '}
            {hover.source.name.toLowerCase()}
          </div>
        </div>
      )}
    </div>
  )
}
