import yaml
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from atc.api.deps import SessionDep
from atc.config import load_config
from atc.schemas import SimulateRequest, SimulationResult
from atc.simulation import simulate as run_simulation

router = APIRouter(tags=["simulation"])


@router.post("/simulate", response_model=SimulationResult)
def simulate(body: SimulateRequest, session: SessionDep) -> SimulationResult:
    """Run the controller over the stored 30-day dataset with optional config overrides.

    Computed in memory and returned directly; nothing is saved, so the API can run on a
    read-only filesystem.
    """
    try:
        base = load_config()
    except (ValidationError, yaml.YAMLError) as exc:
        raise HTTPException(500, f"rules.yaml is invalid: {exc}") from exc
    try:
        config = base.with_overrides(body.overrides)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False, include_context=False)) from exc
    return run_simulation(session, config, body.label)
