"""On-demand simulations, computed in memory and returned directly (nothing is written).

The stored dataset and baseline are loaded once per process and reused, so a warm
serverless instance only pays for running the controller (~1 s).
"""

import threading
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, select

from atc.analytics.charts import build_flows, build_timeseries
from atc.analytics.rows import Population, RunRows, load_population, load_run_rows, rows_from_result
from atc.analytics.summary import build_summary
from atc.config import RulesConfig
from atc.db.models import SimRun
from atc.db.repo import load_customers, load_events
from atc.engine.pipeline import run_controller
from atc.engine.types import AlertRequest, CustomerProfile
from atc.runner import build_profiles, build_requests
from atc.schemas import RunInfo, SimulationResult


@dataclass(frozen=True, slots=True)
class Reference:
    baseline_run_id: str
    requests: list[AlertRequest]
    profiles: Mapping[int, CustomerProfile]
    baseline: RunRows
    people: Population


_reference: Reference | None = None
_lock = threading.Lock()


def reference(session: Session) -> Reference:
    global _reference
    with _lock:
        if _reference is None:
            baseline = session.exec(select(SimRun).where(SimRun.kind == "baseline")).one()
            _reference = Reference(
                baseline_run_id=baseline.id,
                requests=build_requests(load_events(session)),
                profiles=build_profiles(load_customers(session)),
                baseline=load_run_rows(session, baseline.id),
                people=load_population(session),
            )
        return _reference


def simulate(session: Session, config: RulesConfig, label: str | None) -> SimulationResult:
    ref = reference(session)
    started = time.perf_counter()
    result = run_controller(ref.requests, ref.profiles, config)
    atc = rows_from_result(result)
    run_id = f"sim-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(UTC)
    summary = build_summary(
        run_id=run_id,
        baseline_run_id=ref.baseline_run_id,
        label=label,
        created_at=created_at,
        config=config,
        atc=atc,
        base=ref.baseline,
        people=ref.people,
    )
    run = RunInfo(
        id=run_id,
        kind="atc",
        label=label,
        created_at=created_at,
        duration_ms=int((time.perf_counter() - started) * 1000),
        headline={
            "requested": summary.requested,
            "delivered": summary.delivered.atc,
            "reduction_pct": summary.reduction_pct,
            "critical_rate": summary.critical.rate,
            "avg_fatigue": summary.avg_fatigue.atc,
        },
        config=config.model_dump(mode="json"),
    )
    return SimulationResult(
        run=run,
        summary=summary,
        flows=build_flows(atc.rows),
        timeseries=build_timeseries(ref.baseline, atc),
    )
