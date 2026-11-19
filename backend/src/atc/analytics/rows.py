"""One lightweight row per decision, from either the stored snapshot or a fresh engine run.

Analytics work on these rows so that stored runs and on-demand simulations share one
code path.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select as sa_select
from sqlmodel import Session, col, select

from atc.db.models import AlertDecision, Customer, CustomerRunStat, Digest
from atc.engine.pipeline import RunResult


@dataclass(frozen=True, slots=True)
class Row:
    customer_id: int
    event_type: str
    priority: str
    outcome: str
    rule: str
    channels: tuple[str, ...]
    requested_at: datetime
    delivered_at: datetime | None


@dataclass(frozen=True, slots=True)
class RunRows:
    """Everything the summary and charts need about one run."""

    rows: Sequence[Row]
    digest_times: Sequence[datetime]
    fatigue_means: Sequence[float]
    marketing_paused: int


@dataclass(frozen=True, slots=True)
class Population:
    zones: dict[int, ZoneInfo]
    prefs: dict[int, frozenset[str]]

    @property
    def size(self) -> int:
        return len(self.zones)


def load_population(session: Session) -> Population:
    customers = session.exec(select(Customer)).all()
    return Population(
        zones={c.id: ZoneInfo(c.timezone) for c in customers},
        prefs={
            c.id: frozenset(
                ch
                for ch, on in (
                    ("push", c.push_enabled),
                    ("email", c.email_enabled),
                    ("sms", c.sms_enabled),
                )
                if on
            )
            for c in customers
        },
    )


def load_run_rows(session: Session, run_id: str) -> RunRows:
    stmt = sa_select(
        col(AlertDecision.customer_id),
        col(AlertDecision.event_type),
        col(AlertDecision.priority),
        col(AlertDecision.outcome),
        col(AlertDecision.decided_by_rule),
        col(AlertDecision.channels),
        col(AlertDecision.requested_at),
        col(AlertDecision.delivered_at),
    ).where(col(AlertDecision.run_id) == run_id)
    rows = [
        Row(cid, et, pr, oc, rule, tuple(ch), req, dlv)
        for cid, et, pr, oc, rule, ch, req, dlv in session.connection().execute(stmt)
    ]
    digests = session.exec(select(Digest.delivered_at).where(Digest.run_id == run_id)).all()
    stats = session.exec(select(CustomerRunStat).where(CustomerRunStat.run_id == run_id)).all()
    return RunRows(
        rows=rows,
        digest_times=list(digests),
        fatigue_means=[s.fatigue_score_mean for s in stats],
        marketing_paused=sum(s.marketing_paused for s in stats),
    )


def rows_from_result(result: RunResult) -> RunRows:
    rows = [
        Row(
            customer_id=r.request.customer_id,
            event_type=r.request.event_type.value,
            priority=r.request.priority.value,
            outcome=r.decision.outcome.value,
            rule=r.decision.decided_by.value if r.decision.decided_by else "none",
            channels=tuple(c.value for c in r.decision.channels),
            requested_at=r.request.requested_at,
            delivered_at=r.delivered_at,
        )
        for r in result.results
    ]
    return RunRows(
        rows=rows,
        digest_times=[d.deliver_at for d in result.digests],
        fatigue_means=[s.mean for s in result.fatigue.values()],
        marketing_paused=sum(s.marketing_paused for s in result.fatigue.values()),
    )
