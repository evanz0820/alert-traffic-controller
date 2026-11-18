"""Explainable fatigue score (0-100), deliberately not ML.

score = min(100, 100 * weighted_deliveries_last_N_days / saturation)

Each delivery is weighted by priority (critical = 0, so security alerts never make a
customer "fatigued") and multiplied when it landed during the customer's quiet hours.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from atc.config import FatigueGateConfig, QuietHoursConfig
from atc.domain import Priority
from atc.engine.timeutil import in_window
from atc.engine.types import Delivery


@dataclass(frozen=True, slots=True)
class FatigueBreakdown:
    score: float
    weighted: float
    by_priority: dict[Priority, int]
    night_deliveries: int


def fatigue_breakdown(
    deliveries: Iterable[Delivery],
    at: datetime,
    tz: ZoneInfo,
    cfg: FatigueGateConfig,
    quiet: QuietHoursConfig,
) -> FatigueBreakdown:
    window_start = at - timedelta(days=cfg.window_days)
    weighted = 0.0
    night = 0
    counts: dict[Priority, int] = dict.fromkeys(Priority, 0)
    for d in deliveries:
        if not window_start < d.at <= at:
            continue
        weight = cfg.weights[d.priority]
        if weight and in_window(d.at.astimezone(tz).time(), quiet.start, quiet.end):
            weight *= cfg.night_multiplier
            night += 1
        weighted += weight
        counts[d.priority] += 1
    score = min(100.0, 100.0 * weighted / cfg.saturation)
    return FatigueBreakdown(round(score, 1), round(weighted, 2), counts, night)


def fatigue_score(
    deliveries: Iterable[Delivery],
    at: datetime,
    tz: ZoneInfo,
    cfg: FatigueGateConfig,
    quiet: QuietHoursConfig,
) -> float:
    return fatigue_breakdown(deliveries, at, tz, cfg, quiet).score
