"""Headline KPIs for an ATC run versus its paired baseline."""

import statistics
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select as sa_select
from sqlmodel import Session, col, func, select

from atc.config import RulesConfig
from atc.db.models import AlertDecision, Customer, CustomerRunStat, Digest, SimRun
from atc.engine.timeutil import in_window
from atc.schemas import CriticalStats, Pair, Summary

DELIVERED = ("SENT", "DELAYED", "REROUTED")
INTERRUPTING = {"push", "sms"}


@dataclass(frozen=True, slots=True)
class _Row:
    customer_id: int
    priority: str
    outcome: str
    rule: str
    requested_channel: str
    channels: list[str]
    requested_at: datetime
    delivered_at: datetime | None


def _rows(session: Session, run_id: str) -> list[_Row]:
    stmt = sa_select(
        col(AlertDecision.customer_id),
        col(AlertDecision.priority),
        col(AlertDecision.outcome),
        col(AlertDecision.decided_by_rule),
        col(AlertDecision.requested_channel),
        col(AlertDecision.channels),
        col(AlertDecision.requested_at),
        col(AlertDecision.delivered_at),
    ).where(col(AlertDecision.run_id) == run_id)
    return [_Row(*r) for r in session.connection().execute(stmt)]


def _night_interruptions(rows: list[_Row], zones: dict[int, ZoneInfo], config: RulesConfig) -> int:
    quiet = config.rules.quiet_hours
    count = 0
    for r in rows:
        if r.outcome not in DELIVERED or r.delivered_at is None:
            continue
        if not INTERRUPTING.intersection(r.channels):
            continue
        local = r.delivered_at.astimezone(zones[r.customer_id]).time()
        count += in_window(local, quiet.start, quiet.end)
    return count


def _preference_violations(rows: list[_Row], prefs: dict[int, set[str]]) -> int:
    return sum(
        1
        for r in rows
        if r.priority != "critical"
        and r.outcome in DELIVERED
        and any(c not in prefs[r.customer_id] for c in r.channels)
    )


_cache: dict[str, Summary] = {}


def compute_summary(session: Session, run: SimRun) -> Summary:
    if run.id in _cache:
        return _cache[run.id]
    if run.kind != "atc" or run.baseline_run_id is None:
        raise ValueError("summaries are only available for ATC runs")
    config = RulesConfig.model_validate(run.config)
    atc, base = _rows(session, run.id), _rows(session, run.baseline_run_id)

    customers = session.exec(select(Customer)).all()
    zones = {c.id: ZoneInfo(c.timezone) for c in customers}
    prefs = {
        c.id: {ch for ch, on in (("push", c.push_enabled), ("email", c.email_enabled),
                                 ("sms", c.sms_enabled)) if on}
        for c in customers
    }  # fmt: skip
    days = max(1, len({r.requested_at.date() for r in base}))

    digests = session.exec(select(func.count()).where(Digest.run_id == run.id)).one()
    requested = len(base)
    delivered_atc = sum(r.outcome in DELIVERED for r in atc) + digests
    reduction = round(100 * (1 - delivered_atc / requested), 1) if requested else 0.0

    critical = [r for r in atc if r.priority == "critical"]
    crit_sent = [r for r in critical if r.outcome == "SENT"]
    latencies = [
        (r.delivered_at - r.requested_at).total_seconds() for r in crit_sent if r.delivered_at
    ]
    crit_rate = round(100 * len(crit_sent) / len(critical), 2) if critical else 100.0

    outcomes: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for r in atc:
        outcomes[r.outcome] = outcomes.get(r.outcome, 0) + 1
        by_rule[r.rule] = by_rule.get(r.rule, 0) + 1

    def avg_fatigue(run_id: str) -> float:
        value = session.exec(
            select(func.avg(CustomerRunStat.fatigue_score_mean)).where(
                CustomerRunStat.run_id == run_id
            )
        ).one()
        return round(float(value or 0), 1)

    paused = session.exec(
        select(func.count()).where(
            CustomerRunStat.run_id == run.id, col(CustomerRunStat.marketing_paused)
        )
    ).one()

    n_customers = len(customers)
    summary = Summary(
        run_id=run.id,
        baseline_run_id=run.baseline_run_id,
        label=run.label,
        created_at=run.created_at,
        customers=n_customers,
        days=days,
        requested=requested,
        delivered=Pair(baseline=requested, atc=delivered_atc),
        reduction_pct=reduction,
        per_customer_day=Pair(
            baseline=round(requested / n_customers / days, 2),
            atc=round(delivered_atc / n_customers / days, 2),
        ),
        critical=CriticalStats(
            requested=len(critical),
            delivered=len(crit_sent),
            rate=crit_rate,
            median_latency_s=round(statistics.median(latencies), 2) if latencies else 0.0,
            suppressed=sum(r.outcome == "SUPPRESSED" for r in critical),
            delayed=sum(r.outcome == "DELAYED" for r in critical),
        ),
        outcomes=outcomes,
        by_rule=by_rule,
        avg_fatigue=Pair(baseline=avg_fatigue(run.baseline_run_id), atc=avg_fatigue(run.id)),
        night_interruptions=Pair(
            baseline=_night_interruptions(base, zones, config),
            atc=_night_interruptions(atc, zones, config),
        ),
        marketing_delivered=Pair(
            baseline=sum(r.priority == "marketing" for r in base),
            atc=sum(r.priority == "marketing" and r.outcome in DELIVERED for r in atc),
        ),
        preference_violations=Pair(
            baseline=_preference_violations(base, prefs),
            atc=_preference_violations(atc, prefs),
        ),
        duplicates_suppressed=by_rule.get("dedup", 0),
        digests=digests,
        customers_marketing_paused=paused,
        insight=(
            f"ATC cut alert volume {reduction:.0f}% while delivering {crit_rate:.0f}% of "
            f"{len(critical):,} critical alerts."
        ),
    )
    _cache[run.id] = summary
    return summary
