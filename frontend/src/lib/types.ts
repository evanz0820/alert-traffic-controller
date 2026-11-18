// Mirrors backend/src/atc/schemas.py and config.py.

export type Outcome = 'SENT' | 'REROUTED' | 'DELAYED' | 'BATCHED_TO_DIGEST' | 'SUPPRESSED'
export type Priority = 'critical' | 'high' | 'low' | 'marketing'
export type Channel = 'push' | 'email' | 'sms'
export type RuleKey =
  | 'critical_bypass'
  | 'dedup'
  | 'preference_filter'
  | 'fatigue_gate'
  | 'quiet_hours'
  | 'frequency_cap'
  | 'digest'
  | 'channel_routing'
  | 'none'

export interface Pair {
  baseline: number
  atc: number
}

export interface Summary {
  run_id: string
  baseline_run_id: string
  label: string | null
  created_at: string
  customers: number
  days: number
  requested: number
  delivered: Pair
  reduction_pct: number
  per_customer_day: Pair
  critical: {
    requested: number
    delivered: number
    rate: number
    median_latency_s: number
    suppressed: number
    delayed: number
  }
  outcomes: Partial<Record<Outcome, number>>
  by_rule: Partial<Record<RuleKey, number>>
  avg_fatigue: Pair
  night_interruptions: Pair
  marketing_delivered: Pair
  preference_violations: Pair
  duplicates_suppressed: number
  digests: number
  customers_marketing_paused: number
  insight: string
}

export interface RunInfo {
  id: string
  kind: 'atc' | 'baseline'
  label: string | null
  created_at: string
  duration_ms: number
  headline: {
    requested: number
    delivered: number
    reduction_pct: number
    critical_rate: number
    avg_fatigue: number
  }
  config: RulesConfig
}

export interface FlowNode {
  name: string
  kind: 'event' | 'rule' | 'outcome'
  key: string
}
export interface Flows {
  nodes: FlowNode[]
  links: { source: number; target: number; value: number }[]
}

export interface DayPoint {
  date: string
  baseline: number
  atc: number
  critical: number
}

export interface AlertRow {
  alert_id: string
  event_id: number
  customer_id: number
  customer_name: string
  event_type: string
  priority: Priority
  requested_channel: Channel
  final_channel: Channel | null
  channels: Channel[]
  outcome: Outcome
  decided_by_rule: RuleKey
  reason: string
  requested_at: string
  delivered_at: string | null
}

export interface AlertPage {
  items: AlertRow[]
  total: number
  page: number
  page_size: number
}

export interface Replay {
  start: string
  end: string
  event_types: string[]
  outcomes: Outcome[]
  rules: RuleKey[]
  t: number[]
  type: number[]
  priority: number[]
  outcome: number[]
  rule: number[]
  customer: number[]
}

export interface CustomerListItem {
  id: number
  name: string
  segment: string
  engagement: string
  timezone: string
  fatigue_baseline: number | null
  fatigue_atc: number | null
}

export interface AccountInfo {
  id: number
  account_type: string
  partner_code: string | null
  last4: string
  service_phone: string
  service_label: string
}

export interface CustomerDetail {
  id: number
  name: string
  segment: string
  engagement: string
  timezone: string
  push_enabled: boolean
  email_enabled: boolean
  sms_enabled: boolean
  accounts: AccountInfo[]
  fatigue: Pair
  fatigue_peak: Pair
  alerts_delivered: Pair
  marketing_paused: boolean
}

export interface TimelineItem {
  kind: 'alert' | 'digest'
  alert_id: string | null
  event_type: string | null
  priority: Priority | null
  outcome: Outcome
  rule: RuleKey
  explanation: string
  steps: { rule: RuleKey; action: string; detail: string }[]
  requested_at: string | null
  delivered_at: string | null
  channels: Channel[]
  preview: string
  account_last4: string | null
  service_phone: string | null
  digest_count: number | null
}

export interface Timeline {
  customer_id: number
  run_id: string
  baseline: TimelineItem[]
  atc: TimelineItem[]
}

export interface RulesConfig {
  pipeline: RuleKey[]
  rules: {
    critical_bypass: { latency_seconds: Record<Channel, number> }
    dedup: { enabled: boolean }
    preference_filter: { enabled: boolean; fallback_order: Channel[] }
    fatigue_gate: {
      enabled: boolean
      threshold: number
      window_days: number
      saturation: number
      weights: Record<Priority, number>
      night_multiplier: number
    }
    quiet_hours: { enabled: boolean; start: string; end: string; high_amount_exemption: number }
    frequency_cap: {
      enabled: boolean
      daily_cap: number
      hourly_cap: number
      marketing_daily_cap: number
      marketing_weekly_cap: number
    }
    digest: { enabled: boolean; send_at: string; event_types: string[] }
    channel_routing: {
      enabled: boolean
      push_open_window_minutes: number
      open_probability: Record<'high' | 'medium' | 'low', number>
    }
  }
}

export interface AlertFilters {
  outcome?: Outcome[]
  rule?: RuleKey[]
  priority?: Priority[]
  event_type?: string[]
  customer_id?: number
  date_from?: string
  date_to?: string
}
