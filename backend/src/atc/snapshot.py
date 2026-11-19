"""Build the read-only snapshot the app serves: dataset, baseline run, and default run.

Runs at build time (`make seed`), never in the deployed app. Run IDs and timestamps are
fixed so the snapshot is reproducible; tests/integration/test_snapshot.py checks that the
committed file matches what the code produces.
"""

import os
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import insert
from sqlmodel import Session

from atc.analytics.summary import compute_summary
from atc.config import RulesConfig, load_config
from atc.db.models import AlertDecision, CustomerRunStat, Digest, SimRun
from atc.db.repo import load_customers, load_events, reset_schema, write_dataset
from atc.db.session import database_path, make_writable_engine
from atc.engine.pipeline import RunResult, run_baseline, run_controller
from atc.runner import build_profiles, build_requests
from atc.simulator.dataset import build_dataset

BASELINE_RUN_ID = "baseline"
DEFAULT_RUN_ID = "default"
SNAPSHOT_TIME = datetime(2026, 11, 18, tzinfo=UTC)  # end of the simulated month


def _persist(session: Session, run: SimRun, result: RunResult) -> None:
    session.add(run)
    session.flush()
    # Only the ATC run has digests, so ids can simply start at 1.
    digest_ids = list(range(1, len(result.digests) + 1))
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


def build_snapshot(path: Path, config: RulesConfig | None = None) -> SimRun:
    """Write a complete snapshot to `path` (atomically) and return the default run."""
    config = config or load_config()
    tmp = path.with_name(f".{path.name}.building")
    tmp.unlink(missing_ok=True)
    engine = make_writable_engine(tmp)
    reset_schema(engine)
    ds = build_dataset()

    with Session(engine) as session:
        write_dataset(session, ds)
        customers = load_customers(session)
        requests = build_requests(load_events(session))
        profiles = build_profiles(customers)

        started = time.perf_counter()
        baseline = SimRun(
            id=BASELINE_RUN_ID,
            kind="baseline",
            label="Baseline (no controller)",
            seed=ds.seed,
            config={},
            created_at=SNAPSHOT_TIME,
        )
        _persist(session, baseline, run_baseline(requests, profiles, config))
        baseline.duration_ms = int((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        default = SimRun(
            id=DEFAULT_RUN_ID,
            kind="atc",
            label="Default rules",
            baseline_run_id=BASELINE_RUN_ID,
            seed=ds.seed,
            config=config.model_dump(mode="json"),
            created_at=SNAPSHOT_TIME,
        )
        _persist(session, default, run_controller(requests, profiles, config))
        default.duration_ms = int((time.perf_counter() - started) * 1000)
        session.flush()

        summary = compute_summary(session, default)
        default.headline = {
            "requested": summary.requested,
            "delivered": summary.delivered.atc,
            "reduction_pct": summary.reduction_pct,
            "critical_rate": summary.critical.rate,
            "avg_fatigue": summary.avg_fatigue.atc,
        }
        session.add(default)
        session.commit()
        session.refresh(default)
        session.expunge(default)
    engine.dispose()

    with sqlite3.connect(tmp) as conn:
        conn.execute("VACUUM")
    os.replace(tmp, path)
    return default


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else database_path()
    started = time.perf_counter()
    run = build_snapshot(target)
    size_mb = target.stat().st_size / 1e6
    print(
        f"snapshot {target} ({size_mb:.1f} MB): default run "
        f"{run.headline['reduction_pct']}% reduction, "
        f"{run.headline['critical_rate']}% critical, in {time.perf_counter() - started:.1f}s"
    )


if __name__ == "__main__":
    main()
