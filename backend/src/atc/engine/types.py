"""Engine value types. Everything here is immutable, and rules only ever return new values."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import ClassVar, Protocol
from zoneinfo import ZoneInfo

from atc.config import RuleName, RulesConfig
from atc.domain import Channel, Engagement, EventType, Outcome, Priority, priority_of


@dataclass(frozen=True, slots=True)
class AlertRequest:
    alert_id: str
    event_id: int
    source_id: str
    customer_id: int
    account_id: int
    event_type: EventType
    priority: Priority
    requested_channel: Channel
    requested_at: datetime  # tz-aware UTC
    amount: float | None = None

    def __post_init__(self) -> None:
        # Priority is a function of event type. A mismatch would let a fraud alert skip the
        # critical bypass, so it is rejected at construction.
        expected = priority_of(self.event_type)
        if self.priority is not expected:
            raise ValueError(
                f"{self.alert_id}: {self.event_type} must have priority {expected}, "
                f"got {self.priority}"
            )
        if self.requested_at.tzinfo is None:
            raise ValueError(f"{self.alert_id}: requested_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CustomerProfile:
    id: int
    timezone: str
    engagement: Engagement
    enabled_channels: frozenset[Channel]

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class Action(StrEnum):
    PASS = "pass"
    SEND = "send"
    REROUTE = "reroute"
    DELAY = "delay"
    SUPPRESS = "suppress"
    BATCH = "batch"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class Step:
    """One rule's verdict, kept for the plain-English explanation."""

    rule: RuleName
    action: Action
    detail: str


@dataclass(frozen=True, slots=True)
class Decision:
    channel: Channel | None
    scheduled_at: datetime
    outcome: Outcome = Outcome.SENT
    decided_by: RuleName | None = None
    reason: str = "Delivered as requested; no rule needed to intervene."
    terminal: bool = False
    channels: tuple[Channel, ...] = ()
    trace: tuple[Step, ...] = ()

    @classmethod
    def initial(cls, req: AlertRequest) -> "Decision":
        return cls(channel=req.requested_channel, scheduled_at=req.requested_at)

    def note(self, rule: RuleName, action: Action, detail: str) -> "Decision":
        return replace(self, trace=(*self.trace, Step(rule, action, detail)))

    def suppress(self, rule: RuleName, reason: str) -> "Decision":
        return replace(
            self.note(rule, Action.SUPPRESS, reason),
            outcome=Outcome.SUPPRESSED,
            decided_by=rule,
            reason=reason,
            channel=None,
            channels=(),
            terminal=True,
        )

    def batch(self, rule: RuleName, reason: str, deliver_at: datetime) -> "Decision":
        return replace(
            self.note(rule, Action.BATCH, reason),
            outcome=Outcome.BATCHED_TO_DIGEST,
            decided_by=rule,
            reason=reason,
            scheduled_at=deliver_at,
            terminal=True,
        )

    def delay(self, rule: RuleName, reason: str, until: datetime) -> "Decision":
        return replace(
            self.note(rule, Action.DELAY, reason),
            outcome=Outcome.DELAYED,
            decided_by=rule,
            reason=reason,
            scheduled_at=until,
        )

    def reroute(self, rule: RuleName, reason: str, channel: Channel) -> "Decision":
        # DELAYED outranks REROUTED, so a delay already recorded keeps its headline.
        keep = self.outcome is Outcome.DELAYED
        return replace(
            self.note(rule, Action.REROUTE, reason),
            channel=channel,
            outcome=self.outcome if keep else Outcome.REROUTED,
            decided_by=self.decided_by if keep else rule,
            reason=self.reason if keep else reason,
        )


@dataclass(frozen=True, slots=True)
class Delivery:
    at: datetime
    priority: Priority


@dataclass(frozen=True, slots=True)
class CustomerContext:
    """Read-only view of one customer's state at the moment a request is evaluated."""

    profile: CustomerProfile
    deliveries: tuple[Delivery, ...] = ()  # everything scheduled so far (may include future)
    # source_id -> first alert_id; a read-only view supplied by the engine.
    seen_sources: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    fatigue_score: float = 0.0


@dataclass(frozen=True, slots=True)
class DigestRecord:
    customer_id: int
    deliver_at: datetime
    channel: Channel
    alert_ids: tuple[str, ...] = field(default_factory=tuple)


class Rule(Protocol):
    """Shared interface for every pipeline rule. Implementations must be pure."""

    name: ClassVar[RuleName]

    def applies_to(self, req: AlertRequest) -> bool: ...

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision: ...
