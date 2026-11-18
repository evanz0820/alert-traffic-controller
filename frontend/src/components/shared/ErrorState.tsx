import { RotateCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'

/** Unreachable API or a gateway error usually means the backend isn't running. */
function isConnectionProblem(error: unknown) {
  return error instanceof ApiError && (error.status === 0 || error.status >= 502)
}

export function ErrorState({
  error,
  onRetry,
  title = "Couldn't load this data from the ATC API.",
}: {
  error: unknown
  onRetry?: () => void
  title?: string
}) {
  const message = error instanceof Error ? error.message : 'Unknown error'
  return (
    <div className="rounded-2xl border border-rim bg-deck p-6 text-sm" role="alert">
      <p className="font-medium text-ink">{title}</p>
      <p className="mt-1 text-ink-muted">
        {message}.
        {isConnectionProblem(error) && (
          <>
            {' '}
            Start the API with <code>make dev</code> and try again.
          </>
        )}
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          <RotateCw /> Try again
        </Button>
      )}
    </div>
  )
}
