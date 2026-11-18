import { Check, Minus, Phone } from 'lucide-react'
import { ErrorState } from '@/components/shared/ErrorState'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { ACCOUNT_LABEL, fmtInt, SEGMENT_LABEL, zoneLabel } from '@/lib/format'
import { useCustomer, useTimeline } from '@/lib/queries'
import type { CustomerDetail, Timeline } from '@/lib/types'
import { cn } from '@/lib/utils'
import { TimelineList } from './TimelineList'

function FatigueBars({ c }: { c: CustomerDetail }) {
  const rows = [
    { label: 'Without ATC', value: c.fatigue.baseline, bar: 'bg-baseline' },
    { label: 'With ATC', value: c.fatigue.atc, bar: 'bg-sent' },
  ]
  return (
    <div className="space-y-2.5">
      {rows.map((r) => (
        <div
          key={r.label}
          className="grid grid-cols-[88px_minmax(0,1fr)_40px] items-center gap-3 text-xs"
        >
          <span className="text-ink-muted">{r.label}</span>
          <div className="h-1.5 rounded-full bg-console">
            <div className={cn('h-full rounded-full', r.bar)} style={{ width: `${r.value}%` }} />
          </div>
          <span className="text-right num text-ink">{r.value.toFixed(0)}</span>
        </div>
      ))}
    </div>
  )
}

function Channel({ label, on }: { label: string; on: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span
        className={cn(
          'flex size-5 items-center justify-center rounded-full',
          on ? 'bg-sent/15 text-sent' : 'bg-console text-ink-faint',
        )}
      >
        {on ? <Check className="size-3" /> : <Minus className="size-3" />}
      </span>
      <span className={on ? 'text-ink' : 'text-ink-faint'}>
        {label} {on ? 'on' : 'off'}
      </span>
    </li>
  )
}

function Timelines({ timeline, tz }: { timeline: Timeline; tz: string }) {
  const wide = useMediaQuery('(min-width: 1024px)')
  const atcAlerts = timeline.atc.filter(
    (i) => i.kind === 'alert' && i.outcome !== 'SUPPRESSED' && i.outcome !== 'BATCHED_TO_DIGEST',
  ).length
  const digests = timeline.atc.filter((i) => i.kind === 'digest').length
  const before = <TimelineList items={timeline.baseline} tz={tz} showDecision={false} />
  const after = <TimelineList items={timeline.atc} tz={tz} showDecision />
  const beforeTitle = `Without ATC: ${fmtInt(timeline.baseline.length)} alerts`
  const afterTitle = `With ATC: ${fmtInt(atcAlerts)} alerts and ${fmtInt(digests)} digests`

  if (wide) {
    return (
      <div className="grid grid-cols-2 gap-6">
        <section aria-label={beforeTitle}>
          <h3 className="mb-2 text-sm font-medium text-ink-muted">{beforeTitle}</h3>
          {before}
        </section>
        <section aria-label={afterTitle}>
          <h3 className="mb-2 text-sm font-medium text-ink">{afterTitle}</h3>
          {after}
        </section>
      </div>
    )
  }
  return (
    <Tabs defaultValue="atc">
      <TabsList className="w-full">
        <TabsTrigger value="baseline">Without ATC</TabsTrigger>
        <TabsTrigger value="atc">With ATC</TabsTrigger>
      </TabsList>
      <TabsContent value="baseline" className="mt-3">
        <p className="mb-2 text-sm text-ink-muted">{beforeTitle}</p>
        {before}
      </TabsContent>
      <TabsContent value="atc" className="mt-3">
        <p className="mb-2 text-sm text-ink-muted">{afterTitle}</p>
        {after}
      </TabsContent>
    </Tabs>
  )
}

export function CustomerSheet({ id, onClose }: { id: number | null; onClose: () => void }) {
  const customer = useCustomer(id)
  const timeline = useTimeline(id)
  const c = customer.data

  return (
    <Sheet open={id !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side="right"
        className="w-full gap-0 overflow-y-auto border-rim bg-deck p-0 data-[side=right]:w-full data-[side=right]:sm:max-w-2xl data-[side=right]:lg:max-w-5xl"
      >
        <SheetHeader className="border-b border-rim px-5 py-5 sm:px-8">
          <SheetTitle className="text-xl font-semibold text-ink">
            {c ? c.name : <Skeleton className="h-6 w-48" />}
          </SheetTitle>
          <SheetDescription asChild>
            <div className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
              {c ? (
                <>
                  <Badge variant="outline" className="border-rim num">
                    #{c.id}
                  </Badge>
                  <Badge variant="outline" className="border-rim">
                    {SEGMENT_LABEL[c.segment]}
                  </Badge>
                  <Badge variant="outline" className="border-rim">
                    {zoneLabel(c.timezone)} time
                  </Badge>
                  <Badge variant="outline" className="border-rim">
                    {c.engagement[0]!.toUpperCase() + c.engagement.slice(1)} app engagement
                  </Badge>
                  {c.marketing_paused && (
                    <Badge variant="outline" className="border-delayed/40 text-delayed">
                      Marketing paused for fatigue
                    </Badge>
                  )}
                </>
              ) : (
                <Skeleton className="h-5 w-72" />
              )}
            </div>
          </SheetDescription>
        </SheetHeader>

        {c && (
          <div className="grid gap-6 border-b border-rim px-5 py-6 sm:px-8 md:grid-cols-3">
            <section aria-labelledby="accounts-h">
              <h3 id="accounts-h" className="mb-3 text-sm font-medium text-ink">
                Accounts
              </h3>
              <ul className="space-y-2.5">
                {c.accounts.map((a) => (
                  <li key={a.id} className="rounded-lg border border-rim bg-console px-3 py-2.5">
                    <div className="flex items-baseline justify-between gap-2 text-sm">
                      <span className="text-ink">
                        {a.partner_code ? `${a.partner_code} card` : ACCOUNT_LABEL[a.account_type]}
                      </span>
                      <span className="num text-xs text-ink-faint">…{a.last4}</span>
                    </div>
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-ink-muted">
                      <Phone className="size-3" aria-hidden="true" />
                      <span className="truncate">{a.service_label}</span>
                    </div>
                    <div className="mt-0.5 pl-[18px] num text-xs text-ink">{a.service_phone}</div>
                  </li>
                ))}
              </ul>
            </section>
            <section aria-labelledby="prefs-h">
              <h3 id="prefs-h" className="mb-3 text-sm font-medium text-ink">
                Channels they allow
              </h3>
              <ul className="space-y-2">
                <Channel label="Push" on={c.push_enabled} />
                <Channel label="Email" on={c.email_enabled} />
                <Channel label="SMS" on={c.sms_enabled} />
              </ul>
              <p className="mt-3 text-xs leading-relaxed text-ink-faint">
                Security alerts always include SMS, even when it's off.
              </p>
            </section>
            <section aria-labelledby="fatigue-h">
              <h3 id="fatigue-h" className="mb-3 text-sm font-medium text-ink">
                Fatigue score
              </h3>
              <FatigueBars c={c} />
              <p className="mt-3 text-xs text-ink-faint">
                Alerts that reached them:{' '}
                <span className="num text-ink-muted">{fmtInt(c.alerts_delivered.baseline)}</span>{' '}
                before, <span className="num text-ink">{fmtInt(c.alerts_delivered.atc)}</span> with
                ATC.
              </p>
            </section>
          </div>
        )}

        <div className="px-5 py-6 sm:px-8">
          {customer.isError || timeline.isError ? (
            <ErrorState
              error={customer.error ?? timeline.error}
              onRetry={() => {
                customer.refetch()
                timeline.refetch()
              }}
            />
          ) : timeline.data && c ? (
            <Timelines timeline={timeline.data} tz={c.timezone} />
          ) : (
            <div className="space-y-3">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
