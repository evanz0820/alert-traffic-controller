"""Seed the database: synthetic dataset (seed 42). Default runs are added in later stages."""

import time

from sqlmodel import Session

from atc.db.repo import reset_schema, write_dataset
from atc.db.session import engine
from atc.simulator.dataset import build_dataset


def main() -> None:
    started = time.perf_counter()
    ds = build_dataset()
    reset_schema(engine)
    with Session(engine) as session:
        write_dataset(session, ds)
    elapsed = time.perf_counter() - started
    print(
        f"seeded {len(ds.customers)} customers, {len(ds.accounts)} accounts, "
        f"{len(ds.events)} events in {elapsed:.1f}s"
    )


if __name__ == "__main__":
    main()
