"""The controller: runs every alert request through the configured rule pipeline.

`evaluate` is a pure function of (request, customer context, config). `run_controller`
walks the stream in time order and threads per-customer state (what was delivered, which
source ids were seen, pending digests) from one request to the next. No clocks, I/O, or
global randomness, so the same inputs always produce the same decisions.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, time, timedelta
from types import MappingProxyType

from atc.config import RuleName, RulesConfig
from atc.domain import Channel, Outcome, Priority
from atc.engine.fatigue import fatigue_score
from atc.engine.rules import RULES
from atc.engine.timeutil import stable_unit
from atc.engine.types import (
    AlertRequest,
    CustomerContext,
    CustomerProfile,
    Decision,
    Delivery,
    DigestRecord,
    Rule,
)

DELIVERED_OUTCOMES = frozenset({Outcome.SENT, Outcome.DELAYED, Outcome.REROUTED})


class CriticalGuaranteeError(AssertionError):
    """Raised if any code path ever tries to hold back a critical alert."""


@dataclass(frozen=True, slots=True)
class AlertResult:
    request: AlertRequest
    decision: Decision
    delivered_at: datetime | None
    digest_index: int | None = None


@dataclass(frozen=True, slots=True)
class FatigueStat:
    mean: float
    peak: float
    end: float
    delivered: int
    marketing_paused: bool


@dataclass(frozen=True, slots=True)
class RunResult:
    results: tuple[AlertResult, ...]
    digests: tuple[DigestRecord, ...]
    fatigue: Mapping[int, FatigueStat]


@dataclass
class _Ledger:
    deliveries: list[Delivery] = field(default_factory=list)
    seen: dict[str, str] = field(default_factory=dict)
    digests: dict[datetime, int] = field(default_factory=dict)  # deliver_at -> index
    marketing_paused: bool = False


def build_pipeline(config: RulesConfig) -> tuple[Rule, ...]:
    """Enabled rules in configured order. Critical bypass is always first, whatever the
    config says (the config validator rejects anything else, this is defence in depth)."""
    ordered = [RULES[RuleName.CRITICAL_BYPASS]]
    ordered += [
        RULES[name]
        for name in config.pipeline
        if name is not RuleName.CRITICAL_BYPASS and config.is_enabled(name)
    ]
    return tuple(ordered)


def evaluate(
    req: AlertRequest,
    ctx: CustomerContext,
    pipeline: Sequence[Rule],
    config: RulesConfig,
) -> Decision:
    decision = Decision.initial(req)
    for rule in pipeline:
        if decision.terminal:
            break
        if rule.applies_to(req):
            decision = rule.apply(req, decision, ctx, config)
    if not decision.channels and decision.channel is not None:
        decision = replace(decision, channels=(decision.channel,))
    _guard_critical(req, decision)
    return decision


def _guard_critical(req: AlertRequest, decision: Decision) -> None:
    if req.priority is not Priority.CRITICAL:
        return
    if (
        decision.outcome is not Outcome.SENT
        or decision.scheduled_at != req.requested_at
        or Channel.SMS not in decision.channels
    ):
        raise CriticalGuaranteeError(
            f"critical alert {req.alert_id} was not sent instantly: {decision.outcome}"
        )


def dispatch_latency(channel: Channel, alert_id: str, config: RulesConfig) -> timedelta:
    """Simulated provider latency: per-channel base with deterministic jitter (0.8x-1.4x)."""
    base = config.rules.critical_bypass.latency_seconds.get(channel, 2.0)
    return timedelta(seconds=round(base * (0.8 + 0.6 * stable_unit(alert_id, channel)), 3))


def _ordered(requests: Iterable[AlertRequest]) -> list[AlertRequest]:
    return sorted(requests, key=lambda r: (r.requested_at, r.event_id))


def run_controller(
    requests: Iterable[AlertRequest],
    profiles: Mapping[int, CustomerProfile],
    config: RulesConfig,
) -> RunResult:
    pipeline = build_pipeline(config)
    fatigue_cfg, quiet_cfg = config.rules.fatigue_gate, config.rules.quiet_hours
    ledgers: dict[int, _Ledger] = {}
    digests: list[DigestRecord] = []
    results: list[AlertResult] = []

    for req in _ordered(requests):
        profile = profiles[req.customer_id]
        ledger = ledgers.setdefault(req.customer_id, _Ledger())
        ctx = CustomerContext(
            profile=profile,
            deliveries=tuple(ledger.deliveries),
            seen_sources=MappingProxyType(ledger.seen),
            fatigue_score=fatigue_score(
                ledger.deliveries, req.requested_at, profile.tz, fatigue_cfg, quiet_cfg
            ),
        )
        decision = evaluate(req, ctx, pipeline, config)
        ledger.seen.setdefault(req.source_id, req.alert_id)
        if decision.decided_by is RuleName.FATIGUE_GATE:
            ledger.marketing_paused = True

        delivered_at: datetime | None = None
        digest_index: int | None = None
        if decision.outcome in DELIVERED_OUTCOMES and decision.channel is not None:
            first = decision.channels[0] if decision.channels else decision.channel
            delivered_at = decision.scheduled_at + dispatch_latency(first, req.alert_id, config)
            ledger.deliveries.append(Delivery(delivered_at, req.priority))
        elif decision.outcome is Outcome.BATCHED_TO_DIGEST:
            digest_index = ledger.digests.get(decision.scheduled_at)
            if digest_index is None:
                channel = (
                    Channel.EMAIL if Channel.EMAIL in profile.enabled_channels else (Channel.PUSH)
                )
                digest_index = len(digests)
                ledger.digests[decision.scheduled_at] = digest_index
                digests.append(DigestRecord(req.customer_id, decision.scheduled_at, channel))
                ledger.deliveries.append(Delivery(decision.scheduled_at, Priority.LOW))
            record = digests[digest_index]
            digests[digest_index] = DigestRecord(
                record.customer_id,
                record.deliver_at,
                record.channel,
                (*record.alert_ids, req.alert_id),
            )
            delivered_at = decision.scheduled_at
        results.append(AlertResult(req, decision, delivered_at, digest_index))

    fatigue = _fatigue_stats(results, ledgers, profiles, config)
    return RunResult(tuple(results), tuple(digests), MappingProxyType(fatigue))


def run_baseline(
    requests: Iterable[AlertRequest],
    profiles: Mapping[int, CustomerProfile],
    config: RulesConfig,
) -> RunResult:
    """Today's fragmented stack: every request is sent as asked, immediately."""
    ledgers: dict[int, _Ledger] = {}
    results: list[AlertResult] = []
    for req in _ordered(requests):
        ledger = ledgers.setdefault(req.customer_id, _Ledger())
        decision = Decision(
            channel=req.requested_channel,
            scheduled_at=req.requested_at,
            reason="No controller: sent exactly as the upstream system requested.",
            terminal=True,
            channels=(req.requested_channel,),
        )
        delivered_at = req.requested_at + dispatch_latency(
            req.requested_channel, req.alert_id, config
        )
        ledger.deliveries.append(Delivery(delivered_at, req.priority))
        results.append(AlertResult(req, decision, delivered_at))
    fatigue = _fatigue_stats(results, ledgers, profiles, config)
    return RunResult(tuple(results), (), MappingProxyType(fatigue))


def _fatigue_stats(
    results: Sequence[AlertResult],
    ledgers: Mapping[int, _Ledger],
    profiles: Mapping[int, CustomerProfile],
    config: RulesConfig,
) -> dict[int, FatigueStat]:
    """Fatigue sampled at the end of each simulated day (UTC) for every customer."""
    if not results:
        return {}
    first = min(r.request.requested_at for r in results)
    last = max(r.request.requested_at for r in results)
    day = datetime.combine(first.date(), time(), tzinfo=UTC) + timedelta(days=1)
    samples: list[datetime] = []
    while day <= last + timedelta(days=1):
        samples.append(day)
        day += timedelta(days=1)

    fatigue_cfg, quiet_cfg = config.rules.fatigue_gate, config.rules.quiet_hours
    stats: dict[int, FatigueStat] = {}
    for customer_id, profile in profiles.items():
        ledger = ledgers.get(customer_id, _Ledger())
        scores = [
            fatigue_score(ledger.deliveries, at, profile.tz, fatigue_cfg, quiet_cfg)
            for at in samples
        ]
        stats[customer_id] = FatigueStat(
            mean=round(sum(scores) / len(scores), 1),
            peak=max(scores),
            end=scores[-1],
            delivered=len(ledger.deliveries),
            marketing_paused=ledger.marketing_paused,
        )
    return stats
