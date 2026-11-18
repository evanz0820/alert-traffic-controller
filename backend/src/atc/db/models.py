"""SQLModel tables. See docs/PLAN.md §2 for the ER diagram."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Customer(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str = Field(index=True)
    timezone: str
    segment: str = Field(index=True)
    engagement: str
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool


class Account(SQLModel, table=True):
    id: int = Field(primary_key=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    account_type: str
    partner_code: str | None = None
    last4: str
    statement_day: int


class ServicePhone(SQLModel, table=True):
    __tablename__ = "service_phone"

    account_type: str = Field(primary_key=True)
    partner_code: str = Field(default="", primary_key=True)
    phone: str
    label: str


class Event(SQLModel, table=True):
    id: int = Field(primary_key=True)
    source_id: str = Field(index=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    account_id: int = Field(foreign_key="account.id")
    event_type: str = Field(index=True)
    occurred_at: datetime = Field(index=True)
    amount: float | None = None
    campaign_id: str | None = None
    is_retry: bool = False


class SimRun(SQLModel, table=True):
    __tablename__ = "sim_run"

    id: str = Field(primary_key=True)
    kind: str  # "baseline" | "atc"
    label: str | None = None
    baseline_run_id: str | None = Field(default=None, foreign_key="sim_run.id")
    seed: int
    config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime
    duration_ms: int = 0


class AlertDecision(SQLModel, table=True):
    __tablename__ = "alert_decision"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="sim_run.id", index=True)
    alert_id: str
    event_id: int = Field(foreign_key="event.id")
    customer_id: int = Field(foreign_key="customer.id", index=True)
    event_type: str = Field(index=True)
    priority: str = Field(index=True)
    requested_channel: str
    final_channel: str | None = None
    channels: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    outcome: str = Field(index=True)
    decided_by_rule: str = Field(index=True)
    reason: str
    trace: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    requested_at: datetime = Field(index=True)
    delivered_at: datetime | None = None
    digest_id: int | None = Field(default=None, foreign_key="digest.id")


class Digest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="sim_run.id", index=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    delivered_at: datetime
    channel: str
    alert_count: int


class CustomerRunStat(SQLModel, table=True):
    __tablename__ = "customer_run_stat"

    run_id: str = Field(foreign_key="sim_run.id", primary_key=True)
    customer_id: int = Field(foreign_key="customer.id", primary_key=True)
    fatigue_score_end: float
    fatigue_score_peak: float
    alerts_delivered: int
    marketing_paused: bool
