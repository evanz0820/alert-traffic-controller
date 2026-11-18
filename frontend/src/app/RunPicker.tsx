import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useRuns } from '@/lib/queries'
import { useRun } from '@/lib/run-context'

function timeAgo(iso: string) {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  return hours < 24 ? `${hours} h ago` : new Date(iso).toLocaleDateString()
}

function runName(label: string | null, id: string) {
  return label ?? `Run ${id.slice(0, 6)}`
}

export function RunPicker() {
  const { runId, setRunId } = useRun()
  const runs = useRuns()
  if (!runs.data?.length) return null
  const current = runs.data.find((r) => r.id === runId)
  return (
    <div>
      <label htmlFor="run-picker" className="mb-1.5 block text-xs text-ink-faint">
        Simulation run
      </label>
      <Select value={runId} onValueChange={setRunId}>
        <SelectTrigger id="run-picker" className="w-full bg-console">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {runs.data.map((run) => (
            <SelectItem key={run.id} value={run.id}>
              {runName(run.label, run.id)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {current && (
        <p className="mt-1.5 text-xs text-ink-faint">
          <span className="num text-ink-muted">−{current.headline.reduction_pct}%</span> volume, run{' '}
          {timeAgo(current.created_at)}
        </p>
      )}
    </div>
  )
}
