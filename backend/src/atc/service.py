"""Runs simulations end to end: load the stored dataset, run the engine, persist results."""

import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, insert
from sqlmodel import Session, col, func, select

from atc.config import RulesConfig
from atc.db.models import AlertDecision, CustomerRunStat, Digest, SimRun
from atc.db.repo import load_customers, load_events
from atc.engine.pipeline import RunResult, run_baseline, run_controller
from atc.runner import build_profiles, build_requests
from atc.simulator.dataset import DEFAULT_SEED

KEEP_RUNS = 20  # ATC runs retained (oldest pruned); the baseline is always kept


def _persist(session: Session, run: SimRun, result: RunResult) -> None:
    session.add(run)
    session.flush()

    next_id = (session.exec(select(func.max(Digest.id))).one() or 0) + 1
    digest_ids = list(range(next_id, next_id + len(result.digests)))
    if result.digests:
        session.connection().execute(
            insert(Digest),
            [
                {
                    "id": digest_id,
                    "run_id": run.id,
                    "customer_id": d.customer_id,
                    "delivered_at": d.deliver_at,
                    "channel": d.channel.value,
                    "alert_count": len(d.alert_ids),
                }
                for digest_id, d in zip(digest_ids, result.digests, strict=True)
            ],
        )

    rows: list[dict[str, Any]] = []
    for r in result.results:
        req, dec = r.request, r.decision
        rows.append(
            {
                "run_id": run.id,
                "alert_id": req.alert_id,
                "event_id": req.event_id,
                "customer_id": req.customer_id,
                "event_type": req.event_type.value,
                "priority": req.priority.value,
                "requested_channel": req.requested_channel.value,
                "final_channel": dec.channel.value if dec.channel else None,
                "channels": [c.value for c in dec.channels],
                "outcome": dec.outcome.value,
                "decided_by_rule": dec.decided_by.value if dec.decided_by else "none",
                "reason": dec.reason,
                "trace": [
                    {"rule": s.rule.value, "action": s.action.value, "detail": s.detail}
                    for s in dec.trace
                ],
                "requested_at": req.requested_at,
                "delivered_at": r.delivered_at,
                "digest_id": digest_ids[r.digest_index] if r.digest_index is not None else None,
            }
        )
    session.connection().execute(insert(AlertDecision), rows)

    session.connection().execute(
        insert(CustomerRunStat),
        [
            {
                "run_id": run.id,
                "customer_id": cid,
                "fatigue_score_mean": s.mean,
                "fatigue_score_peak": s.peak,
                "fatigue_score_end": s.end,
                "alerts_delivered": s.delivered,
                "marketing_paused": s.marketing_paused,
            }
            for cid, s in result.fatigue.items()
        ],
    )


def ensure_baseline(session: Session, config: RulesConfig) -> SimRun:
    existing = session.exec(select(SimRun).where(SimRun.kind == "baseline")).first()
    if existing is not None:
        return existing
    started = time.perf_counter()
    customers = load_customers(session)
    requests = build_requests(load_events(session))
    result = run_baseline(requests, build_profiles(customers), config)
    run = SimRun(
        id=f"baseline-{uuid.uuid4().hex[:8]}",
        kind="baseline",
        label="Baseline (no controller)",
        seed=DEFAULT_SEED,
        config={},
        created_at=datetime.now(UTC),
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    _persist(session, run, result)
    session.commit()
    return run


def execute_run(session: Session, config: RulesConfig, label: str | None = None) -> SimRun:
    """Run the controller with `config` against the stored dataset and persist everything."""
    from atc.analytics.summary import compute_summary

    baseline = ensure_baseline(session, config)
    started = time.perf_counter()
    customers = load_customers(session)
    requests = build_requests(load_events(session))
    result = run_controller(requests, build_profiles(customers), config)
    run = SimRun(
        id=uuid.uuid4().hex[:12],
        kind="atc",
        label=label,
        baseline_run_id=baseline.id,
        seed=baseline.seed,
        config=config.model_dump(mode="json"),
        created_at=datetime.now(UTC),
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    _persist(session, run, result)
    session.flush()
    summary = compute_summary(session, run)
    run.headline = {
        "requested": summary.requested,
        "delivered": summary.delivered.atc,
        "reduction_pct": summary.reduction_pct,
        "critical_rate": summary.critical.rate,
        "avg_fatigue": summary.avg_fatigue.atc,
    }
    session.add(run)
    session.commit()
    _prune(session)
    return run


def _prune(session: Session) -> None:
    runs: Sequence[SimRun] = session.exec(
        select(SimRun).where(SimRun.kind == "atc").order_by(col(SimRun.created_at).desc())
    ).all()
    stale = [r.id for r in runs[KEEP_RUNS:]]
    if not stale:
        return
    for table in (AlertDecision, Digest, CustomerRunStat):
        session.connection().execute(delete(table).where(col(table.run_id).in_(stale)))
    session.connection().execute(delete(SimRun).where(col(SimRun.id).in_(stale)))
    session.commit()
