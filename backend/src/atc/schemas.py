"""API response models shared by analytics and routers."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Pair(BaseModel):
    baseline: int | float
    atc: int | float


class CriticalStats(BaseModel):
    requested: int
    delivered: int
    rate: float
    median_latency_s: float
    suppressed: int
    delayed: int


class Summary(BaseModel):
    run_id: str
    baseline_run_id: str
    label: str | None
    created_at: datetime
    customers: int
    days: int
    requested: int
    delivered: Pair
    reduction_pct: float
    per_customer_day: Pair
    critical: CriticalStats
    outcomes: dict[str, int]
    by_rule: dict[str, int]
    avg_fatigue: Pair
    night_interruptions: Pair
    marketing_delivered: Pair
    preference_violations: Pair
    duplicates_suppressed: int
    digests: int
    customers_marketing_paused: int
    insight: str


class SimulateRequest(BaseModel):
    overrides: dict[str, Any] = Field(default_factory=dict)
    label: str | None = Field(default=None, max_length=80)


class RunInfo(BaseModel):
    id: str
    kind: str
    label: str | None
    created_at: datetime
    duration_ms: int
    headline: dict[str, Any]
    config: dict[str, Any]


class FlowNode(BaseModel):
    name: str
    kind: str  # "event" | "rule" | "outcome"
    key: str


class FlowLink(BaseModel):
    source: int
    target: int
    value: int


class Flows(BaseModel):
    nodes: list[FlowNode]
    links: list[FlowLink]


class DayPoint(BaseModel):
    date: str
    baseline: int
    atc: int
    critical: int


class AlertRow(BaseModel):
    alert_id: str
    event_id: int
    customer_id: int
    customer_name: str
    event_type: str
    priority: str
    requested_channel: str
    final_channel: str | None
    channels: list[str]
    outcome: str
    decided_by_rule: str
    reason: str
    requested_at: datetime
    delivered_at: datetime | None


class AlertPage(BaseModel):
    items: list[AlertRow]
    total: int
    page: int
    page_size: int


class Replay(BaseModel):
    start: datetime
    end: datetime
    event_types: list[str]
    outcomes: list[str]
    rules: list[str]
    t: list[int]  # seconds since start
    type: list[int]
    priority: list[int]  # 0 marketing, 1 low, 2 high, 3 critical
    outcome: list[int]
    rule: list[int]
    customer: list[int]


class CustomerListItem(BaseModel):
    id: int
    name: str
    segment: str
    engagement: str
    timezone: str
    fatigue_baseline: float | None = None
    fatigue_atc: float | None = None


class AccountInfo(BaseModel):
    id: int
    account_type: str
    partner_code: str | None
    last4: str
    service_phone: str
    service_label: str


class CustomerDetail(BaseModel):
    id: int
    name: str
    segment: str
    engagement: str
    timezone: str
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    accounts: list[AccountInfo]
    fatigue: Pair
    fatigue_peak: Pair
    alerts_delivered: Pair
    marketing_paused: bool


class TimelineStep(BaseModel):
    rule: str
    action: str
    detail: str


class TimelineItem(BaseModel):
    kind: str  # "alert" | "digest"
    alert_id: str | None
    event_type: str | None
    priority: str | None
    outcome: str
    rule: str
    explanation: str
    steps: list[TimelineStep]
    requested_at: datetime | None
    delivered_at: datetime | None
    channels: list[str]
    preview: str
    account_last4: str | None
    service_phone: str | None
    digest_count: int | None = None


class Timeline(BaseModel):
    customer_id: int
    run_id: str
    baseline: list[TimelineItem]
    atc: list[TimelineItem]


class SimulationResult(BaseModel):
    """An on-demand run, computed in memory and returned whole; it is not stored."""

    run: RunInfo
    summary: Summary
    flows: Flows
    timeseries: list[DayPoint]
