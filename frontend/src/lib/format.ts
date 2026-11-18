import type { Outcome, Priority, RuleKey } from './types'

const int = new Intl.NumberFormat('en-US')
export const fmtInt = (n: number) => int.format(Math.round(n))
export const fmtPct = (n: number, digits = 0) => `${n.toFixed(digits)}%`
export const fmtDec = (n: number, digits = 1) => n.toFixed(digits)

export function fmtDateTime(iso: string, timeZone?: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone,
  })
}

export function fmtTime(iso: string, timeZone?: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone,
    timeZoneName: 'short',
  })
}

export function fmtDay(isoDate: string) {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

export const OUTCOME_LABEL: Record<Outcome, string> = {
  SENT: 'Sent',
  REROUTED: 'Rerouted',
  DELAYED: 'Delayed',
  BATCHED_TO_DIGEST: 'Batched',
  SUPPRESSED: 'Suppressed',
}

/** Tailwind token per outcome. Rerouted is still delivered, so it shares the sent hue. */
export const OUTCOME_TONE: Record<Outcome, 'sent' | 'delayed' | 'batched' | 'suppressed'> = {
  SENT: 'sent',
  REROUTED: 'sent',
  DELAYED: 'delayed',
  BATCHED_TO_DIGEST: 'batched',
  SUPPRESSED: 'suppressed',
}

export const RULE_LABEL: Record<RuleKey, string> = {
  critical_bypass: 'Critical bypass',
  dedup: 'Deduplication',
  preference_filter: 'Preference filter',
  fatigue_gate: 'Fatigue gate',
  quiet_hours: 'Quiet hours',
  frequency_cap: 'Frequency cap',
  digest: 'Digest batching',
  channel_routing: 'Channel routing',
  none: 'No intervention',
}

export const PRIORITY_LABEL: Record<Priority, string> = {
  critical: 'Critical',
  high: 'High',
  low: 'Low',
  marketing: 'Marketing',
}

export const EVENT_LABEL: Record<string, string> = {
  deposit: 'Deposit',
  low_balance: 'Low balance',
  large_transaction: 'Large transaction',
  international_transaction: 'International transaction',
  fraud_suspected: 'Fraud suspected',
  card_locked: 'Card locked',
  new_device_login: 'New device login',
  payment_due_soon: 'Payment due soon',
  payment_received: 'Payment received',
  statement_ready: 'Statement ready',
  credit_limit_change: 'Credit limit change',
  marketing_offer: 'Marketing offer',
}

export const SEGMENT_LABEL: Record<string, string> = {
  mass: 'Mass market',
  mass_affluent: 'Mass affluent',
  senior: 'Senior',
}

export const ACCOUNT_LABEL: Record<string, string> = {
  checking: 'Checking',
  savings: 'Savings',
  northgate_card: 'Northgate card',
  cobrand_card: 'Cobrand card',
}

export function zoneLabel(tz: string) {
  return tz.split('/').pop()!.replace('_', ' ')
}
