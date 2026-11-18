import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** A bezel-like surface for an instrument: title row, optional aside, then content. */
export function Panel({
  title,
  description,
  aside,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode
  description?: ReactNode
  aside?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}) {
  return (
    <section className={cn('rounded-2xl border border-rim bg-deck', className)}>
      {(title || aside) && (
        <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5 sm:px-6">
          <div>
            {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
            {description && <p className="mt-1 text-sm text-ink-muted">{description}</p>}
          </div>
          {aside}
        </div>
      )}
      <div className={cn('p-5 sm:p-6', bodyClassName)}>{children}</div>
    </section>
  )
}
