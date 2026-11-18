from fastapi import APIRouter

from atc.config import RulesConfig, load_config, save_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=RulesConfig)
def get_config() -> RulesConfig:
    return load_config()


@router.put("", response_model=RulesConfig)
def put_config(config: RulesConfig) -> RulesConfig:
    """Validate and persist the full rules configuration to rules.yaml."""
    save_config(config)
    return config
