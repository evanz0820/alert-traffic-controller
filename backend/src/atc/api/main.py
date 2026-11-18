"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="Alert Traffic Controller",
    description="Member-first alert gateway for Northgate Bank (synthetic data).",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
