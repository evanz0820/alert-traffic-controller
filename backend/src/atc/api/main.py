"""FastAPI application entry point. OpenAPI docs are served at /docs."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session, select

from atc.api.routers import config, customers, runs, simulate
from atc.db.models import SimRun
from atc.db.session import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    with Session(engine) as session:
        if session.exec(select(SimRun).where(SimRun.kind == "atc")).first() is None:
            from atc.seed import seed

            seed(engine)
    yield


app = FastAPI(
    title="Alert Traffic Controller",
    description=(
        "A member-first alert gateway for the fictional Northgate Bank. Every alert passes "
        "through one controller that decides what to send, when, and on which channel. "
        "Critical alerts are never suppressed or delayed. All data is synthetic."
    ),
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(simulate.router)
app.include_router(runs.router)
app.include_router(customers.router)
app.include_router(config.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
