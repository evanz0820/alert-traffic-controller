import { ExternalLink, ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { Panel } from '@/components/shared/Panel'
import { fmtInt } from '@/lib/format'
import { useSummary } from '@/lib/queries'

const LINKEDIN_POST =
  'https://engineering.linkedin.com/blog/2018/03/air-traffic-controller--member-first-notifications-at-linkedin'

function Prose({ children }: { children: ReactNode }) {
  return (
    <div className="max-w-[68ch] space-y-4 text-[15px] leading-relaxed text-ink-muted [&_strong]:font-medium [&_strong]:text-ink">
      {children}
    </div>
  )
}

const STAGES = [
  { title: 'Simulator', detail: '500 customers, 30 days, seed 42' },
  { title: 'Event stream', detail: 'retries, bursts, 3 AM batch jobs' },
  { title: 'Rules pipeline', detail: '8 pure rules, critical first' },
  { title: 'Decision log', detail: 'SQLite, one row per alert' },
  { title: 'API', detail: 'FastAPI, OpenAPI at /docs' },
  { title: 'Dashboard', detail: 'React, Recharts, canvas' },
]

/** Left-to-right on desktop, top-to-bottom on mobile. The pipeline step is highlighted. */
function Architecture() {
  return (
    <figure>
      <ol className="grid gap-3 md:grid-cols-6 md:gap-0">
        {STAGES.map((stage, i) => (
          <li key={stage.title} className="relative flex md:flex-col md:items-stretch">
            <div
              className={
                i === 2
                  ? 'flex-1 rounded-xl border border-sent/50 bg-sent/10 px-4 py-3 md:mx-2'
                  : 'flex-1 rounded-xl border border-rim bg-console px-4 py-3 md:mx-2'
              }
            >
              <div
                className={
                  i === 2 ? 'text-sm font-medium text-sent' : 'text-sm font-medium text-ink'
                }
              >
                {stage.title}
              </div>
              <div className="mt-1 text-xs leading-snug text-ink-faint">{stage.detail}</div>
            </div>
            {i < STAGES.length - 1 && (
              <svg
                aria-hidden="true"
                viewBox="0 0 16 16"
                className="absolute -bottom-3 left-6 size-3 text-ink-faint md:top-1/2 md:-right-1.5 md:bottom-auto md:left-auto md:-translate-y-1/2 md:-rotate-90"
              >
                <path d="M8 2v11M3 9l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.6" />
              </svg>
            )}
          </li>
        ))}
      </ol>
      <figcaption className="mt-4 text-sm text-ink-muted">
        The same stored event stream feeds two passes: a baseline that sends everything as
        requested, and the controller. Every chart compares the two.
      </figcaption>
    </figure>
  )
}

const ORDER = [
  ['Critical bypass', 'Nothing may run before it, so nothing can touch a fraud alert.'],
  ['Deduplication', 'Drop retries before they count against caps or fatigue.'],
  ['Preference filter', 'Fix the channel before later rules reason about it.'],
  ['Fatigue gate', 'Pause marketing for tired customers before it spends cap budget.'],
  ['Quiet hours', 'Shift alerts to morning so caps count them on the right day.'],
  ['Frequency cap', 'Ration what is left; cut marketing first, move low alerts to the digest.'],
  ['Digest batching', 'Bundle routine updates into one daily message.'],
  ['Channel routing', 'Pick the best channel last, once the alert is definitely going out.'],
]

const NEXT = [
  [
    'Opt-out prediction',
    'Replace the heuristic fatigue score with a model trained on unsubscribes, keeping the rule-based guardrails.',
  ],
  [
    'Real delivery providers',
    'Push, email and SMS adapters with delivery receipts, so open-rate fallback uses real signals.',
  ],
  [
    'Streaming',
    'Run the same pure rules as a Kafka consumer with per-customer state in a key-value store.',
  ],
  [
    'A/B holdouts',
    'Keep a random slice of customers on the old stack to measure opt-out and call-center impact causally.',
  ],
  [
    'Per-segment policy',
    'Different caps and quiet hours for seniors, small business and premium segments.',
  ],
]

export default function AboutPage() {
  const summary = useSummary()
  const s = summary.data

  return (
    <>
      <header className="mb-10 max-w-[68ch]">
        <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-ink sm:text-[36px]">
          One controller between a bank and its customers' phones.
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">
          Alert Traffic Controller is a portfolio project. Northgate Bank, its customers and every
          alert here are synthetic.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="The problem">
          <Prose>
            <p>
              At a typical retail bank, balance, transaction, fraud, payment, statement and
              marketing alerts are each fired by a different system. None of them knows what the
              others just sent. The customer gets the sum: a statement email at 3 AM, a deposit
              push, a retried duplicate, two offers before breakfast.
            </p>
            <p>
              Volume isn't the real cost. Customers who are buried in alerts turn them off, and then
              the one alert that matters,{' '}
              <strong>"Did you just spend $900 in another country?"</strong>, never reaches them.
            </p>
          </Prose>
        </Panel>

        <Panel title="The inspiration">
          <Prose>
            <p>
              In 2018 LinkedIn described how they fixed the same problem for notifications: route
              every message through a single gateway, the{' '}
              <a
                href={LINKEDIN_POST}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sent underline decoration-sent/40 underline-offset-2 hover:decoration-sent"
              >
                Air Traffic Controller
                <ExternalLink className="size-3.5" aria-hidden="true" />
              </a>
              , which decides what to send, when and on which channel based on each member's history
              and preferences.
            </p>
            <p>
              This project applies that idea to banking, where one class of message carries a hard
              rule LinkedIn didn't have: <strong>security alerts can never be held back</strong>. It
              draws on my time supporting customer alerts on a core banking platform, including
              routing each customer to the right service line for bank-branded versus cobrand cards.
            </p>
          </Prose>
        </Panel>
      </div>

      <Panel className="mt-6" title="How it fits together">
        <Architecture />
      </Panel>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Panel
          title="Why the rule order matters"
          description="Rules run top to bottom; the first rule to make a final call wins."
        >
          <ol className="space-y-3">
            {ORDER.map(([name, why], i) => (
              <li key={name} className="grid grid-cols-[28px_minmax(0,1fr)] gap-3 text-sm">
                <span className="pt-px num text-ink-faint">{String(i + 1).padStart(2, '0')}</span>
                <span>
                  <span className={i === 0 ? 'font-medium text-critical' : 'font-medium text-ink'}>
                    {name}.
                  </span>{' '}
                  <span className="text-ink-muted">{why}</span>
                </span>
              </li>
            ))}
          </ol>
        </Panel>

        <Panel
          title={
            <span className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-critical" aria-hidden="true" />
              The critical guarantee
            </span>
          }
        >
          <Prose>
            <p>
              Fraud, card lock and new-device alerts go out instantly on SMS plus every channel the
              customer has on. This is enforced four times:
            </p>
            <ul className="list-disc space-y-2 pl-5 text-sm">
              <li>The critical bypass always runs first and ends evaluation.</li>
              <li>Config validation rejects any pipeline that moves or disables it.</li>
              <li>A runtime guard raises if a critical decision is ever not sent instantly.</li>
              <li>
                Property-based tests generate thousands of random event streams and random rule
                configs and check that critical requested equals critical sent.
              </li>
            </ul>
            {s && (
              <p>
                In the selected run: <strong className="num">{fmtInt(s.critical.delivered)}</strong>{' '}
                of <strong className="num">{fmtInt(s.critical.requested)}</strong> critical alerts
                delivered, median <strong className="num">{s.critical.median_latency_s}s</strong>.
              </p>
            )}
          </Prose>
        </Panel>
      </div>

      <Panel className="mt-6" title="What I'd build next">
        <dl className="grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
          {NEXT.map(([title, detail]) => (
            <div key={title}>
              <dt className="text-sm font-medium text-ink">{title}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-ink-muted">{detail}</dd>
            </div>
          ))}
        </dl>
      </Panel>
    </>
  )
}
