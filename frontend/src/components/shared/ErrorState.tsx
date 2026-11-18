import { RotateCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Unknown error'
  return (
    <div className="rounded-2xl border border-rim bg-deck p-6 text-sm" role="alert">
      <p className="font-medium text-ink">Couldn't load this data from the ATC API.</p>
      <p className="mt-1 text-ink-muted">
        {message}. Check that the API is running on port 8000 (<code>make dev</code>).
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          <RotateCw /> Try again
        </Button>
      )}
    </div>
  )
}
