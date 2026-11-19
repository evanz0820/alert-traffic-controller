"""FastAPI application. Every route lives under /api; OpenAPI docs are at /api/docs.

Locally `make dev` serves it with uvicorn; on Vercel `api/index.py` exposes the same app
as a Python function.
"""

from fastapi import APIRouter, FastAPI

from atc.api.routers import config, customers, runs, simulate

app = FastAPI(
    title="Alert Traffic Controller",
    description=(
        "A member-first alert gateway for the fictional Northgate Bank. Every alert passes "
        "through one controller that decides what to send, when, and on which channel. "
        "Critical alerts are never suppressed or delayed. All data is synthetic, and the "
        "API is read-only: stored runs come from a prebuilt snapshot and simulations are "
        "computed on demand."
    ),
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

api = APIRouter(prefix="/api")
api.include_router(simulate.router)
api.include_router(runs.router)
api.include_router(customers.router)
api.include_router(config.router)


@api.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api)
