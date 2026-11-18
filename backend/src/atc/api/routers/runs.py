import csv
import io
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlmodel import col, func, select

from atc.analytics.charts import flows, replay, timeseries
from atc.analytics.summary import compute_summary
from atc.api.deps import SessionDep, get_atc_run
from atc.db.models import AlertDecision, Customer, SimRun
from atc.schemas import AlertPage, AlertRow, DayPoint, Flows, Replay, RunInfo, Summary

router = APIRouter(prefix="/runs", tags=["runs"])

ListParam = Annotated[list[str] | None, Query()]


@router.get("", response_model=list[RunInfo])
def list_runs(session: SessionDep, limit: Annotated[int, Query(ge=1, le=50)] = 10) -> list[RunInfo]:
    runs = session.exec(
        select(SimRun)
        .where(SimRun.kind == "atc")
        .order_by(col(SimRun.created_at).desc())
        .limit(limit)
    ).all()
    return [RunInfo.model_validate(r, from_attributes=True) for r in runs]


@router.get("/{run_id}/summary", response_model=Summary)
def run_summary(run_id: str, session: SessionDep) -> Summary:
    return compute_summary(session, get_atc_run(session, run_id))


@router.get("/{run_id}/flows", response_model=Flows)
def run_flows(run_id: str, session: SessionDep) -> Flows:
    return flows(session, get_atc_run(session, run_id).id)


@router.get("/{run_id}/timeseries", response_model=list[DayPoint])
def run_timeseries(run_id: str, session: SessionDep) -> list[DayPoint]:
    return timeseries(session, get_atc_run(session, run_id))


@router.get("/{run_id}/replay", response_model=Replay)
def run_replay(run_id: str, session: SessionDep) -> Replay:
    return replay(session, get_atc_run(session, run_id).id)


def _filtered(
    run_id: str,
    outcome: list[str] | None,
    rule: list[str] | None,
    priority: list[str] | None,
    event_type: list[str] | None,
    customer_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Any:
    stmt: Any = select(AlertDecision, Customer.name).join(
        Customer, col(Customer.id) == col(AlertDecision.customer_id)
    )
    stmt = stmt.where(AlertDecision.run_id == run_id)
    if outcome:
        stmt = stmt.where(col(AlertDecision.outcome).in_(outcome))
    if rule:
        stmt = stmt.where(col(AlertDecision.decided_by_rule).in_(rule))
    if priority:
        stmt = stmt.where(col(AlertDecision.priority).in_(priority))
    if event_type:
        stmt = stmt.where(col(AlertDecision.event_type).in_(event_type))
    if customer_id is not None:
        stmt = stmt.where(AlertDecision.customer_id == customer_id)
    if date_from is not None:
        stmt = stmt.where(col(AlertDecision.requested_at) >= date_from)
    if date_to is not None:
        stmt = stmt.where(col(AlertDecision.requested_at) < date_to)
    return stmt


def _row(decision: AlertDecision, name: str) -> AlertRow:
    return AlertRow(customer_name=name, **decision.model_dump(exclude={"id", "run_id", "trace"}))


@router.get("/{run_id}/alerts", response_model=AlertPage)
def run_alerts(
    run_id: str,
    session: SessionDep,
    outcome: ListParam = None,
    rule: ListParam = None,
    priority: ListParam = None,
    event_type: ListParam = None,
    customer_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    sort: Literal["requested_at", "-requested_at"] = "requested_at",
) -> AlertPage:
    run = get_atc_run(session, run_id)
    stmt = _filtered(run.id, outcome, rule, priority, event_type, customer_id, date_from, date_to)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    order = col(AlertDecision.requested_at)
    stmt = stmt.order_by(order.desc() if sort.startswith("-") else order, col(AlertDecision.id))
    rows = session.exec(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return AlertPage(
        items=[_row(d, n) for d, n in rows], total=total, page=page, page_size=page_size
    )


CSV_COLUMNS = [
    "alert_id", "event_id", "customer_id", "customer_name", "event_type", "priority",
    "requested_channel", "final_channel", "outcome", "decided_by_rule", "reason",
    "requested_at", "delivered_at",
]  # fmt: skip


@router.get("/{run_id}/alerts.csv", response_class=StreamingResponse)
def run_alerts_csv(
    run_id: str,
    session: SessionDep,
    outcome: ListParam = None,
    rule: ListParam = None,
    priority: ListParam = None,
    event_type: ListParam = None,
    customer_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> StreamingResponse:
    run = get_atc_run(session, run_id)
    stmt = _filtered(
        run.id, outcome, rule, priority, event_type, customer_id, date_from, date_to
    ).order_by(col(AlertDecision.requested_at), col(AlertDecision.id))
    rows = session.exec(stmt).all()

    def generate() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for decision, name in rows:
            writer.writerow(_row(decision, name).model_dump(mode="json"))
            if buffer.tell() > 64_000:
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate()
        yield buffer.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="atc-alerts-{run.id}.csv"'},
    )
