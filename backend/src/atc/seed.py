"""Seed the database: synthetic dataset (seed 42), the baseline, and the default ATC run."""

import time

from sqlalchemy import Engine
from sqlmodel import Session

from atc.config import load_config
from atc.db.repo import reset_schema, write_dataset
from atc.db.session import engine as default_engine
from atc.service import ensure_baseline, execute_run
from atc.simulator.dataset import build_dataset


def seed(engine: Engine = default_engine) -> None:
    started = time.perf_counter()
    ds = build_dataset()
    reset_schema(engine)
    config = load_config()
    with Session(engine) as session:
        write_dataset(session, ds)
        ensure_baseline(session, config)
        run = execute_run(session, config, label="Default rules")
    print(
        f"seeded {len(ds.customers)} customers, {len(ds.accounts)} accounts, "
        f"{len(ds.events)} events; default run {run.id} "
        f"({run.headline['reduction_pct']}% reduction) in {time.perf_counter() - started:.1f}s"
    )


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
