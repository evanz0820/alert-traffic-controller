"""Chart data: Sankey flows, daily volumes, and the compact Live Tower replay."""

from collections import Counter
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select as sa_select
from sqlmodel import Session, col

from atc.analytics.rows import Row, RunRows, load_run_rows
from atc.db.models import AlertDecision, SimRun
from atc.domain import EventType, Outcome
from atc.schemas import DayPoint, FlowLink, FlowNode, Flows, Replay

BANK_TZ = ZoneInfo("America/New_York")  # Northgate reports on Eastern time
DELIVERED = ("SENT", "DELAYED", "REROUTED")

EVENT_LABELS: dict[str, str] = {
    "deposit": "Deposit",
    "low_balance": "Low balance",
    "large_transaction": "Large transaction",
    "international_transaction": "International txn",
    "fraud_suspected": "Fraud suspected",
    "card_locked": "Card locked",
    "new_device_login": "New device login",
    "payment_due_soon": "Payment due soon",
    "payment_received": "Payment received",
    "statement_ready": "Statement ready",
    "credit_limit_change": "Credit limit change",
    "marketing_offer": "Marketing offer",
}
RULE_LABELS: dict[str, str] = {
    "critical_bypass": "Critical bypass",
    "dedup": "Deduplication",
    "preference_filter": "Preference filter",
    "fatigue_gate": "Fatigue gate",
    "quiet_hours": "Quiet hours",
    "frequency_cap": "Frequency cap",
    "digest": "Digest batching",
    "channel_routing": "Channel routing",
    "none": "No intervention",
}
OUTCOME_LABELS: dict[str, str] = {
    "SENT": "Sent",
    "REROUTED": "Rerouted",
    "DELAYED": "Delayed",
    "BATCHED_TO_DIGEST": "Batched to digest",
    "SUPPRESSED": "Suppressed",
}


def build_flows(rows: Sequence[Row]) -> Flows:
    """event type -> deciding rule -> outcome, ordered for a readable Sankey."""
    counts = Counter((r.event_type, r.rule, r.outcome) for r in rows)

    events = [e.value for e in EventType if any(k[0] == e.value for k in counts)]
    rules = [k for k in RULE_LABELS if any(c[1] == k for c in counts)]
    outcomes = [o for o in OUTCOME_LABELS if any(c[2] == o for c in counts)]

    nodes = (
        [FlowNode(name=EVENT_LABELS[e], kind="event", key=e) for e in events]
        + [FlowNode(name=RULE_LABELS[r], kind="rule", key=r) for r in rules]
        + [FlowNode(name=OUTCOME_LABELS[o], kind="outcome", key=o) for o in outcomes]
    )
    index = {("event", e): i for i, e in enumerate(events)}
    index |= {("rule", r): len(events) + i for i, r in enumerate(rules)}
    index |= {("outcome", o): len(events) + len(rules) + i for i, o in enumerate(outcomes)}

    first: dict[tuple[int, int], int] = {}
    second: dict[tuple[int, int], int] = {}
    for (event_type, rule, outcome), count in counts.items():
        a = (index[("event", event_type)], index[("rule", rule)])
        b = (index[("rule", rule)], index[("outcome", outcome)])
        first[a] = first.get(a, 0) + count
        second[b] = second.get(b, 0) + count
    links = [FlowLink(source=s, target=t, value=v) for (s, t), v in {**first, **second}.items()]
    return Flows(nodes=nodes, links=links)


def flows(session: Session, run_id: str) -> Flows:
    return build_flows(load_run_rows(session, run_id).rows)


def _bank_day(at: datetime) -> date:
    return at.astimezone(BANK_TZ).date()


def build_timeseries(base: RunRows, atc: RunRows) -> list[DayPoint]:
    delivered = [r.delivered_at for r in base.rows if r.delivered_at is not None]
    if not delivered:
        return []
    # The dataset starts at midnight UTC, i.e. mid-evening Eastern; skip that partial day.
    first_full_day = min(delivered).date()
    days = sorted({d for t in delivered if (d := _bank_day(t)) >= first_full_day})
    span = [days[0] + timedelta(days=i) for i in range((days[-1] - days[0]).days + 1)]
    baseline = dict.fromkeys(span, 0)
    atc_count = dict.fromkeys(span, 0)
    critical = dict.fromkeys(span, 0)

    for t in delivered:
        if (d := _bank_day(t)) in baseline:
            baseline[d] += 1
    for r in atc.rows:
        if r.outcome not in DELIVERED or r.delivered_at is None:
            continue
        if (d := _bank_day(r.delivered_at)) in atc_count:
            atc_count[d] += 1
            critical[d] += r.priority == "critical"
    for t in atc.digest_times:
        if (d := _bank_day(t)) in atc_count:
            atc_count[d] += 1
    return [
        DayPoint(date=d.isoformat(), baseline=baseline[d], atc=atc_count[d], critical=critical[d])
        for d in span
    ]


def timeseries(session: Session, run: SimRun) -> list[DayPoint]:
    assert run.baseline_run_id is not None
    return build_timeseries(
        load_run_rows(session, run.baseline_run_id), load_run_rows(session, run.id)
    )


PRIORITY_INDEX = {"marketing": 0, "low": 1, "high": 2, "critical": 3}


def replay(session: Session, run_id: str) -> Replay:
    rows = (
        session.connection()
        .execute(
            sa_select(
                col(AlertDecision.requested_at),
                col(AlertDecision.event_type),
                col(AlertDecision.priority),
                col(AlertDecision.outcome),
                col(AlertDecision.decided_by_rule),
                col(AlertDecision.customer_id),
            )
            .where(col(AlertDecision.run_id) == run_id)
            .order_by(col(AlertDecision.requested_at), col(AlertDecision.event_id))
        )
        .all()
    )
    events = [e.value for e in EventType]
    outcomes = [o.value for o in Outcome]
    rules = list(RULE_LABELS)
    start = rows[0][0] if rows else datetime.now().astimezone()
    end = rows[-1][0] if rows else start
    return Replay(
        start=start,
        end=end,
        event_types=events,
        outcomes=outcomes,
        rules=rules,
        t=[int((r[0] - start).total_seconds()) for r in rows],
        type=[events.index(r[1]) for r in rows],
        priority=[PRIORITY_INDEX[r[2]] for r in rows],
        outcome=[outcomes.index(r[3]) for r in rows],
        rule=[rules.index(r[4]) for r in rows],
        customer=[r[5] for r in rows],
    )
