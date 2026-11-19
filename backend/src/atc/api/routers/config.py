from fastapi import APIRouter

from atc.config import RulesConfig, load_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=RulesConfig)
def get_config() -> RulesConfig:
    """The rules configuration in rules.yaml (read-only; edit the file and rebuild)."""
    return load_config()
