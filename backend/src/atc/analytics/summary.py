"""Headline KPIs for an ATC run versus its paired baseline."""

import statistics
from collections.abc import Sequence
from datetime import datetime

from sqlmodel import Session

from atc.analytics.rows import Population, Row, RunRows, load_population, load_run_rows
from atc.config import RulesConfig
from atc.db.models import SimRun
from atc.engine.timeutil import in_window
from atc.schemas import CriticalStats, Pair, Summary

DELIVERED = ("SENT", "DELAYED", "REROUTED")
INTERRUPTING = {"push", "sms"}


def _night_interruptions(rows: Sequence[Row], people: Population, config: RulesConfig) -> int:
    quiet = config.rules.quiet_hours
    count = 0
    for r in rows:
        if r.outcome not in DELIVERED or r.delivered_at is None:
            continue
        if not INTERRUPTING.intersection(r.channels):
            continue
        local = r.delivered_at.astimezone(people.zones[r.customer_id]).time()
        count += in_window(local, quiet.start, quiet.end)
    return count


def _preference_violations(rows: Sequence[Row], people: Population) -> int:
    return sum(
        1
        for r in rows
        if r.priority != "critical"
        and r.outcome in DELIVERED
        and any(c not in people.prefs[r.customer_id] for c in r.channels)
    )


def _mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def build_summary(
    *,
    run_id: str,
    baseline_run_id: str,
    label: str | None,
    created_at: datetime,
    config: RulesConfig,
    atc: RunRows,
    base: RunRows,
    people: Population,
) -> Summary:
    """Pure: KPIs from rows, used for both stored runs and in-memory simulations."""
    days = max(1, len({r.requested_at.date() for r in base.rows}))
    digests = len(atc.digest_times)
    requested = len(base.rows)
    delivered_atc = sum(r.outcome in DELIVERED for r in atc.rows) + digests
    reduction = round(100 * (1 - delivered_atc / requested), 1) if requested else 0.0

    critical = [r for r in atc.rows if r.priority == "critical"]
    crit_sent = [r for r in critical if r.outcome == "SENT"]
    latencies = [
        (r.delivered_at - r.requested_at).total_seconds() for r in crit_sent if r.delivered_at
    ]
    crit_rate = round(100 * len(crit_sent) / len(critical), 2) if critical else 100.0

    outcomes: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for r in atc.rows:
        outcomes[r.outcome] = outcomes.get(r.outcome, 0) + 1
        by_rule[r.rule] = by_rule.get(r.rule, 0) + 1

    n = max(1, people.size)
    return Summary(
        run_id=run_id,
        baseline_run_id=baseline_run_id,
        label=label,
        created_at=created_at,
        customers=people.size,
        days=days,
        requested=requested,
        delivered=Pair(baseline=requested, atc=delivered_atc),
        reduction_pct=reduction,
        per_customer_day=Pair(
            baseline=round(requested / n / days, 2),
            atc=round(delivered_atc / n / days, 2),
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
        avg_fatigue=Pair(baseline=_mean(base.fatigue_means), atc=_mean(atc.fatigue_means)),
        night_interruptions=Pair(
            baseline=_night_interruptions(base.rows, people, config),
            atc=_night_interruptions(atc.rows, people, config),
        ),
        marketing_delivered=Pair(
            baseline=sum(r.priority == "marketing" for r in base.rows),
            atc=sum(r.priority == "marketing" and r.outcome in DELIVERED for r in atc.rows),
        ),
        preference_violations=Pair(
            baseline=_preference_violations(base.rows, people),
            atc=_preference_violations(atc.rows, people),
        ),
        duplicates_suppressed=by_rule.get("dedup", 0),
        digests=digests,
        customers_marketing_paused=atc.marketing_paused,
        insight=(
            f"ATC cut alert volume {reduction:.0f}% while delivering {crit_rate:.0f}% of "
            f"{len(critical):,} critical alerts."
        ),
    )


def compute_summary(session: Session, run: SimRun) -> Summary:
    """Summary for a run stored in the snapshot."""
    if run.kind != "atc" or run.baseline_run_id is None:
        raise ValueError("summaries are only available for ATC runs")
    return build_summary(
        run_id=run.id,
        baseline_run_id=run.baseline_run_id,
        label=run.label,
        created_at=run.created_at,
        config=RulesConfig.model_validate(run.config),
        atc=load_run_rows(session, run.id),
        base=load_run_rows(session, run.baseline_run_id),
        people=load_population(session),
    )
