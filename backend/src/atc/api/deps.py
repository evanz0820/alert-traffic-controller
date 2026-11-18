"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session, col, select

from atc.db.models import SimRun
from atc.db.session import get_session

SessionDep = Annotated[Session, Depends(get_session)]


def get_atc_run(session: Session, run_id: str | None) -> SimRun:
    """Resolve an ATC run by id, or the latest one when no id is given."""
    if run_id is None:
        run = session.exec(
            select(SimRun).where(SimRun.kind == "atc").order_by(col(SimRun.created_at).desc())
        ).first()
    else:
        run = session.get(SimRun, run_id)
    if run is None:
        raise HTTPException(404, f"run {run_id or '(latest)'} not found")
    if run.kind != "atc":
        raise HTTPException(400, "baseline runs have no controller results; pass an ATC run id")
    return run
