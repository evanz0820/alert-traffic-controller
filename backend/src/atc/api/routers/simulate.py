import yaml
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from atc.api.deps import SessionDep
from atc.config import load_config
from atc.schemas import SimulateRequest, SimulateResponse
from atc.service import execute_run

router = APIRouter(tags=["simulation"])


@router.post("/simulate", response_model=SimulateResponse, status_code=201)
def simulate(body: SimulateRequest, session: SessionDep) -> SimulateResponse:
    """Run the controller over the stored 30-day dataset with optional config overrides."""
    try:
        base = load_config()
    except (ValidationError, yaml.YAMLError) as exc:
        raise HTTPException(500, f"rules.yaml is invalid: {exc}") from exc
    try:
        config = base.with_overrides(body.overrides)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False, include_context=False)) from exc
    run = execute_run(session, config, label=body.label)
    assert run.baseline_run_id is not None
    return SimulateResponse(
        run_id=run.id, baseline_run_id=run.baseline_run_id, duration_ms=run.duration_ms
    )
