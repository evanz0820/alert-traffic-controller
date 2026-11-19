from pathlib import Path

from sqlmodel import Session, select

from atc.db.models import ServicePhone
from atc.db.repo import load_accounts, load_customers, load_events, reset_schema, write_dataset
from atc.db.session import make_writable_engine
from atc.directory.phones import SERVICE_PHONES
from atc.simulator.models import Dataset


def test_dataset_round_trips_through_sqlite(tmp_path: Path, dataset: Dataset) -> None:
    engine = make_writable_engine(tmp_path / "atc.db")
    reset_schema(engine)
    with Session(engine) as session:
        write_dataset(session, dataset)

    with Session(engine) as session:
        assert tuple(load_customers(session)) == dataset.customers
        assert tuple(load_accounts(session)) == dataset.accounts
        rows = load_events(session)
        assert [i for i, _ in rows] == list(range(1, len(dataset.events) + 1))
        assert tuple(e for _, e in rows) == dataset.events
        assert len(session.exec(select(ServicePhone)).all()) == len(SERVICE_PHONES)
