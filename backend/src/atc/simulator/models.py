"""Plain, immutable records produced by the simulator (no database concerns)."""

from dataclasses import dataclass
from datetime import date, datetime

from atc.domain import AccountType, Engagement, EventType, Segment


@dataclass(frozen=True, slots=True)
class SimCustomer:
    id: int
    name: str
    timezone: str
    segment: Segment
    engagement: Engagement
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool


@dataclass(frozen=True, slots=True)
class SimAccount:
    id: int
    customer_id: int
    account_type: AccountType
    partner_code: str | None
    last4: str
    statement_day: int  # day of month the statement cuts (also drives payment cycle)


@dataclass(frozen=True, slots=True)
class SimEvent:
    source_id: str  # idempotency key; upstream retries reuse it
    customer_id: int
    account_id: int
    event_type: EventType
    occurred_at: datetime  # tz-aware UTC
    amount: float | None = None
    campaign_id: str | None = None
    is_retry: bool = False  # True for injected duplicate deliveries


@dataclass(frozen=True, slots=True)
class Dataset:
    seed: int
    start: date
    days: int
    customers: tuple[SimCustomer, ...]
    accounts: tuple[SimAccount, ...]
    events: tuple[SimEvent, ...]  # sorted by occurred_at
