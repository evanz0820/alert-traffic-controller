import type { RuleKey } from '@/lib/types'

export const RULE_INFO: Record<Exclude<RuleKey, 'none'>, { name: string; summary: string }> = {
  critical_bypass: {
    name: 'Critical bypass',
    summary:
      'Fraud, card lock and new-device alerts skip every other rule and go out at once on SMS plus every channel the customer has on.',
  },
  dedup: {
    name: 'Deduplication',
    summary: 'Upstream systems retry. A second copy of the same event is dropped, not sent again.',
  },
  preference_filter: {
    name: 'Preference filter',
    summary:
      'Never uses a channel the customer turned off; moves the alert to the next one they allow.',
  },
  fatigue_gate: {
    name: 'Fatigue gate',
    summary: 'Pauses marketing for customers who have had a heavy week of alerts.',
  },
  quiet_hours: {
    name: 'Quiet hours',
    summary:
      "Holds non-critical alerts overnight in the customer's own time zone; very large transactions still go through.",
  },
  frequency_cap: {
    name: 'Frequency cap',
    summary:
      'Limits non-critical alerts per day and per hour. Marketing is cut first; low-priority alerts move to the digest.',
  },
  digest: {
    name: 'Digest batching',
    summary:
      'Bundles deposits, payments received, statements and limit changes into one daily summary.',
  },
  channel_routing: {
    name: 'Channel routing',
    summary:
      'Push first for engaged app users, email first for everyone else; unread pushes follow up by email.',
  },
}
