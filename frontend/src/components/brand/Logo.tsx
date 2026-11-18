import { useId } from 'react'
import { cn } from '@/lib/utils'

/**
 * Original mark: a control tower (windowed cab on a tapered shaft) inside a radar scope,
 * with a sweep and a single tracked contact.
 */
export function Logo({ className }: { className?: string }) {
  const sweep = useId()
  return (
    <svg viewBox="0 0 32 32" className={cn('size-8', className)} aria-hidden="true">
      <defs>
        <linearGradient id={sweep} x1="16" y1="16" x2="22" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--sent)" stopOpacity="0" />
          <stop offset="1" stopColor="var(--sent)" stopOpacity="0.55" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="14.25" fill="none" stroke="currentColor" strokeOpacity="0.35" />
      <circle cx="16" cy="16" r="9" fill="none" stroke="currentColor" strokeOpacity="0.18" />
      <path d="M16 16 V1.75 A14.25 14.25 0 0 1 28.34 8.88 Z" fill={`url(#${sweep})`} />
      <path d="M16 16 L28.34 8.88" stroke="var(--sent)" strokeWidth="1.1" strokeLinecap="round" />
      <path d="M14.2 13.2 L12.9 24 H19.1 L17.8 13.2 Z" fill="currentColor" />
      <rect x="10.6" y="8.6" width="10.8" height="4.4" rx="1" fill="currentColor" />
      <path d="M12.4 10.8 H19.6" stroke="var(--night)" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M12.6 7.4 H19.4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M10.5 24.6 H21.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="23.6" cy="9.4" r="1.5" fill="var(--sent)" />
    </svg>
  )
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <Logo className="text-ink" />
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight text-ink">Northgate ATC</div>
        <div className="text-xs text-ink-faint">Alert Traffic Controller</div>
      </div>
    </div>
  )
}
