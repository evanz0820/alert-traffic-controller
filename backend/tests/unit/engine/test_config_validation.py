import pytest
from pydantic import ValidationError

from atc.config import RulesConfig


@pytest.mark.parametrize(
    "overrides",
    [
        {"rules": {"critical_bypass": {"latency_seconds": {"sms": 7200, "push": 1, "email": 1}}}},
        {"rules": {"critical_bypass": {"latency_seconds": {"sms": -1, "push": 1, "email": 1}}}},
        {
            "rules": {
                "fatigue_gate": {"weights": {"critical": 1, "high": 1, "low": 1, "marketing": 1}}
            }
        },
        {"rules": {"preference_filter": {"fallback_order": []}}},
        {"rules": {"preference_filter": {"fallback_order": ["push", "push"]}}},
    ],
    ids=[
        "latency-hours",
        "latency-negative",
        "critical-weight-nonzero",
        "fallback-empty",
        "fallback-duplicate",
    ],
)
def test_unsafe_or_partial_config_is_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RulesConfig().with_overrides(overrides)


@pytest.mark.parametrize(
    ("rule", "field", "partial"),
    [
        ("critical_bypass", "latency_seconds", {"sms": 1.0}),
        ("channel_routing", "open_probability", {"high": 0.7}),
        ("fatigue_gate", "weights", {"high": 1, "low": 1, "marketing": 1}),
    ],
)
def test_full_config_with_partial_map_is_rejected(
    rule: str, field: str, partial: dict[str, float]
) -> None:
    """PUT /config and rules.yaml replace maps wholesale (unlike merged overrides)."""
    data = RulesConfig().model_dump(mode="json")
    data["rules"][rule][field] = partial
    with pytest.raises(ValidationError, match="every key"):
        RulesConfig.model_validate(data)
