from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from atc.config import RulesConfig
from atc.domain import Priority
from atc.engine.fatigue import fatigue_breakdown, fatigue_score
from atc.engine.types import Delivery

NY = ZoneInfo("America/New_York")
# 2026-10-20 20:00 EDT
NOW = datetime(2026, 10, 21, 0, 0, tzinfo=UTC)
# 2026-10-20 11:00 EDT
DAYTIME = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
# 2026-10-19 23:00 EDT
NIGHT = datetime(2026, 10, 20, 3, 0, tzinfo=UTC)


def _score(deliveries: list[Delivery], config: RulesConfig | None = None) -> float:
    cfg = config or RulesConfig()
    return fatigue_score(deliveries, NOW, NY, cfg.rules.fatigue_gate, cfg.rules.quiet_hours)


def test_no_deliveries_scores_zero() -> None:
    assert _score([]) == 0.0


def test_critical_deliveries_weigh_nothing() -> None:
    assert _score([Delivery(DAYTIME, Priority.CRITICAL)] * 50) == 0.0


@pytest.mark.parametrize(
    ("priority", "expected"),
    [(Priority.HIGH, 5.6), (Priority.LOW, 3.3), (Priority.MARKETING, 8.3)],
)
def test_daytime_delivery_weighted_by_priority(priority: Priority, expected: float) -> None:
    assert _score([Delivery(DAYTIME, priority)]) == expected


def test_deliveries_outside_window_ignored() -> None:
    old = NOW - timedelta(days=7)
    future = NOW + timedelta(minutes=1)
    assert _score([Delivery(old, Priority.HIGH), Delivery(future, Priority.HIGH)]) == 0.0
    assert _score([Delivery(old + timedelta(seconds=1), Priority.HIGH)]) > 0


def test_window_days_configurable() -> None:
    narrow = RulesConfig().with_overrides({"rules": {"fatigue_gate": {"window_days": 1}}})
    two_days_ago = Delivery(NOW - timedelta(days=2), Priority.HIGH)
    assert _score([two_days_ago]) > 0
    assert _score([two_days_ago], narrow) == 0.0


def test_night_multiplier_applied() -> None:
    day = _score([Delivery(DAYTIME, Priority.HIGH)])
    night = _score([Delivery(NIGHT, Priority.HIGH)])
    assert day == 5.6
    assert night == 8.3


def test_score_capped_at_100() -> None:
    assert _score([Delivery(DAYTIME, Priority.MARKETING)] * 100) == 100.0


def test_breakdown_counts() -> None:
    cfg = RulesConfig()
    deliveries = [
        Delivery(DAYTIME, Priority.HIGH),
        Delivery(NIGHT, Priority.HIGH),
        Delivery(NIGHT, Priority.CRITICAL),
        Delivery(DAYTIME, Priority.LOW),
        Delivery(DAYTIME, Priority.MARKETING),
        Delivery(NOW - timedelta(days=10), Priority.MARKETING),
    ]
    b = fatigue_breakdown(deliveries, NOW, NY, cfg.rules.fatigue_gate, cfg.rules.quiet_hours)
    assert b.by_priority == {
        Priority.CRITICAL: 1,
        Priority.HIGH: 2,
        Priority.LOW: 1,
        Priority.MARKETING: 1,
    }
    assert b.night_deliveries == 1
    assert b.weighted == pytest.approx(1.0 + 1.5 + 0.6 + 1.5)
    assert b.score == round(100 * b.weighted / 18, 1)
