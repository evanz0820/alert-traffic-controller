"""Rules configuration: a single `rules.yaml` validated into `RulesConfig`.

The dashboard edits the same file through `PUT /config`, so every knob lives here.
"""

import os
from datetime import time
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

from atc.domain import Channel, Engagement, EventType, Priority


class RuleName(StrEnum):
    CRITICAL_BYPASS = "critical_bypass"
    DEDUP = "dedup"
    PREFERENCE_FILTER = "preference_filter"
    FATIGUE_GATE = "fatigue_gate"
    QUIET_HOURS = "quiet_hours"
    FREQUENCY_CAP = "frequency_cap"
    DIGEST = "digest"
    CHANNEL_ROUTING = "channel_routing"


DEFAULT_ORDER: tuple[RuleName, ...] = tuple(RuleName)

# Wall-clock time serialised as "HH:MM" (YAML- and slider-friendly).
Clock = Annotated[time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuleToggle(_Model):
    enabled: bool = True


class CriticalBypassConfig(_Model):
    """Not toggleable: critical alerts are always delivered. Latencies drive the simulated
    dispatch time per channel (seconds)."""

    latency_seconds: dict[Channel, float] = Field(
        default_factory=lambda: {Channel.SMS: 0.9, Channel.PUSH: 1.2, Channel.EMAIL: 2.8}
    )


class DedupConfig(RuleToggle):
    pass


class PreferenceFilterConfig(RuleToggle):
    fallback_order: tuple[Channel, ...] = (Channel.PUSH, Channel.EMAIL, Channel.SMS)


class FatigueGateConfig(RuleToggle):
    threshold: Annotated[float, Field(ge=0, le=100)] = 60.0
    window_days: Annotated[int, Field(ge=1, le=30)] = 7
    # Weighted deliveries in the window that map to a score of 100.
    saturation: Annotated[float, Field(gt=0)] = 18.0
    weights: dict[Priority, float] = Field(
        default_factory=lambda: {
            Priority.CRITICAL: 0.0,
            Priority.HIGH: 1.0,
            Priority.LOW: 0.6,
            Priority.MARKETING: 1.5,
        }
    )
    night_multiplier: Annotated[float, Field(ge=1)] = 1.5


class QuietHoursConfig(RuleToggle):
    start: Clock = time(22, 0)
    end: Clock = time(7, 0)
    high_amount_exemption: Annotated[float, Field(ge=0)] = 2500.0


class FrequencyCapConfig(RuleToggle):
    daily_cap: Annotated[int, Field(ge=1, le=50)] = 5
    hourly_cap: Annotated[int, Field(ge=1, le=20)] = 2
    marketing_daily_cap: Annotated[int, Field(ge=0, le=10)] = 1
    marketing_weekly_cap: Annotated[int, Field(ge=0, le=20)] = 2


class DigestConfig(RuleToggle):
    send_at: Clock = time(18, 0)
    event_types: tuple[EventType, ...] = (
        EventType.DEPOSIT,
        EventType.PAYMENT_RECEIVED,
        EventType.STATEMENT_READY,
        EventType.CREDIT_LIMIT_CHANGE,
    )

    @field_validator("event_types")
    @classmethod
    def _only_low_priority(cls, value: tuple[EventType, ...]) -> tuple[EventType, ...]:
        from atc.domain import priority_of

        bad = [e for e in value if priority_of(e) in (Priority.CRITICAL, Priority.HIGH)]
        if bad:
            raise ValueError(f"only low or marketing alerts can be digested, got {bad}")
        return value


class ChannelRoutingConfig(RuleToggle):
    push_open_window_minutes: Annotated[int, Field(ge=1, le=1440)] = 30
    open_probability: dict[Engagement, Annotated[float, Field(ge=0, le=1)]] = Field(
        default_factory=lambda: {
            Engagement.HIGH: 0.75,
            Engagement.MEDIUM: 0.5,
            Engagement.LOW: 0.25,
        }
    )


class RulesSettings(_Model):
    critical_bypass: CriticalBypassConfig = CriticalBypassConfig()
    dedup: DedupConfig = DedupConfig()
    preference_filter: PreferenceFilterConfig = PreferenceFilterConfig()
    fatigue_gate: FatigueGateConfig = FatigueGateConfig()
    quiet_hours: QuietHoursConfig = QuietHoursConfig()
    frequency_cap: FrequencyCapConfig = FrequencyCapConfig()
    digest: DigestConfig = DigestConfig()
    channel_routing: ChannelRoutingConfig = ChannelRoutingConfig()


class RulesConfig(_Model):
    pipeline: tuple[RuleName, ...] = DEFAULT_ORDER
    rules: RulesSettings = RulesSettings()

    @model_validator(mode="after")
    def _critical_bypass_first(self) -> Self:
        if not self.pipeline or self.pipeline[0] is not RuleName.CRITICAL_BYPASS:
            raise ValueError("critical_bypass must be the first rule in the pipeline")
        if len(set(self.pipeline)) != len(self.pipeline):
            raise ValueError("pipeline contains duplicate rules")
        return self

    def is_enabled(self, rule: RuleName) -> bool:
        if rule is RuleName.CRITICAL_BYPASS:
            return True
        toggle = getattr(self.rules, rule.value)
        assert isinstance(toggle, RuleToggle)
        return toggle.enabled

    def with_overrides(self, overrides: dict[str, object]) -> "RulesConfig":
        """Deep-merge a partial dict (as sent by the dashboard) and re-validate."""
        merged = _deep_merge(self.model_dump(mode="json"), overrides)
        return RulesConfig.model_validate(merged)


def _deep_merge(base: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    out = dict(base)
    for key, value in patch.items():
        current = out.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            out[key] = _deep_merge(current, value)
        else:
            out[key] = value
    return out


DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "rules.yaml"


def rules_path() -> Path:
    return Path(os.environ.get("ATC_RULES_PATH", DEFAULT_RULES_PATH))


def load_config(path: Path | None = None) -> RulesConfig:
    target = path or rules_path()
    if not target.exists():
        return RulesConfig()
    data = yaml.safe_load(target.read_text()) or {}
    return RulesConfig.model_validate(data)


def save_config(config: RulesConfig, path: Path | None = None) -> None:
    target = path or rules_path()
    header = (
        "# ATC rules configuration. Edited by hand or from the dashboard (PUT /config).\n"
        "# critical_bypass is always first and cannot be disabled.\n"
    )
    body = yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False)
    target.write_text(header + body)
