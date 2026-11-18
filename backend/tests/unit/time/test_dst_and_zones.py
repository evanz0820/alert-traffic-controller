"""Quiet hours across time zones and the Nov 1, 2026 fall-back DST boundary."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from atc.config import RulesConfig
from atc.domain import Channel, Engagement, EventType, Outcome, Priority
from atc.engine.pipeline import build_pipeline, evaluate
from atc.engine.timeutil import format_local, in_window, next_local_time
from atc.engine.types import AlertRequest, CustomerContext, CustomerProfile, Decision

CONFIG = RulesConfig().with_overrides({"rules": {"channel_routing": {"enabled": False}}})
PIPELINE = build_pipeline(CONFIG)
ALL = frozenset(Channel)


def _request(at: datetime, priority: Priority = Priority.HIGH) -> AlertRequest:
    return AlertRequest(
        alert_id="A-000001",
        event_id=1,
        source_id="src-1",
        customer_id=1,
        account_id=1,
        event_type=EventType.LOW_BALANCE if priority is Priority.HIGH else EventType.DEPOSIT,
        priority=priority,
        requested_channel=Channel.PUSH,
        requested_at=at,
    )


def _ctx(zone: str) -> CustomerContext:
    return CustomerContext(profile=CustomerProfile(1, zone, Engagement.HIGH, ALL))


def _evaluate(at: datetime, zone: str) -> Decision:
    return evaluate(_request(at), _ctx(zone), PIPELINE, CONFIG)


@pytest.mark.parametrize(
    ("t", "expected"),
    [(time(21, 59), False), (time(22, 0), True), (time(3, 0), True), (time(6, 59), True),
     (time(7, 0), False), (time(12, 0), False)],
)  # fmt: skip
def test_overnight_window_wraps_midnight(t: time, expected: bool) -> None:
    assert in_window(t, time(22, 0), time(7, 0)) is expected


def test_daytime_window_does_not_wrap() -> None:
    assert in_window(time(13, 0), time(12, 0), time(14, 0))
    assert not in_window(time(23, 0), time(12, 0), time(14, 0))


def test_same_instant_is_quiet_in_one_zone_and_not_another() -> None:
    at = datetime(2026, 10, 20, 3, 30, tzinfo=UTC)  # 11:30 PM ET, 8:30 PM PT
    ny = _evaluate(at, "America/New_York")
    la = _evaluate(at, "America/Los_Angeles")
    assert ny.outcome is Outcome.DELAYED
    assert la.outcome is Outcome.SENT


@pytest.mark.parametrize(
    "zone",
    ["America/New_York", "America/Chicago", "America/Denver", "America/Phoenix",
     "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu"],
)  # fmt: skip
def test_delayed_alerts_release_at_7am_local_in_every_zone(zone: str) -> None:
    tz = ZoneInfo(zone)
    at = datetime(2026, 10, 21, 23, 15, tzinfo=tz).astimezone(UTC)
    decision = _evaluate(at, zone)
    released = decision.scheduled_at.astimezone(tz)
    assert decision.outcome is Outcome.DELAYED
    assert (released.date().isoformat(), released.hour, released.minute) == ("2026-10-22", 7, 0)


def test_fall_back_night_releases_at_7am_standard_time() -> None:
    """The night of Oct 31 → Nov 1 is 25 hours long in New York; 7 AM is EST, not EDT."""
    tz = ZoneInfo("America/New_York")
    at = datetime(2026, 10, 31, 23, 0, tzinfo=tz).astimezone(UTC)  # 03:00 UTC Nov 1, EDT
    release = next_local_time(at, tz, time(7, 0))
    assert release == datetime(2026, 11, 1, 12, 0, tzinfo=UTC)  # 7 AM EST = UTC-5
    assert (release - at).total_seconds() == 9 * 3600  # 8 wall-clock hours + the repeated hour
    assert format_local(release, tz) == "7:00 AM EST"


def test_ambiguous_1am_hour_is_quiet_both_times() -> None:
    """1:30 AM happens twice on Nov 1; both occurrences are inside quiet hours."""
    tz = ZoneInfo("America/Chicago")
    first = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)  # 1:30 AM CDT
    second = datetime(2026, 11, 1, 7, 30, tzinfo=UTC)  # 1:30 AM CST
    for at in (first, second):
        assert at.astimezone(tz).hour == 1
        decision = _evaluate(at, "America/Chicago")
        assert decision.outcome is Outcome.DELAYED
        assert decision.scheduled_at == datetime(2026, 11, 1, 13, 0, tzinfo=UTC)  # 7 AM CST


def test_spring_forward_release_is_still_7am_local() -> None:
    tz = ZoneInfo("America/Denver")
    at = datetime(2026, 3, 8, 1, 30, tzinfo=tz).astimezone(UTC)  # before the 2 AM jump
    release = next_local_time(at, tz, time(7, 0))
    assert release == datetime(2026, 3, 8, 13, 0, tzinfo=UTC)  # 7 AM MDT = UTC-6


def test_phoenix_ignores_dst() -> None:
    tz = ZoneInfo("America/Phoenix")
    before = next_local_time(datetime(2026, 10, 31, 12, tzinfo=UTC), tz, time(7, 0))
    after = next_local_time(datetime(2026, 11, 2, 12, tzinfo=UTC), tz, time(7, 0))
    assert before.hour == after.hour == 14  # 7 AM MST = 14:00 UTC year-round


def test_next_local_time_is_inclusive_of_exact_target() -> None:
    tz = ZoneInfo("America/New_York")
    at = datetime(2026, 10, 20, 7, 0, tzinfo=tz)
    assert next_local_time(at, tz, time(7, 0)) == at.astimezone(UTC)


def test_digest_time_respects_dst() -> None:
    tz = ZoneInfo("America/New_York")
    before = next_local_time(datetime(2026, 10, 30, 12, tzinfo=UTC), tz, time(18, 0))
    after = next_local_time(datetime(2026, 11, 2, 12, tzinfo=UTC), tz, time(18, 0))
    assert before.hour == 22  # 6 PM EDT
    assert after.hour == 23  # 6 PM EST


@pytest.mark.parametrize("target", [time(1, 0), time(1, 30), time(1, 59), time(2, 30)])
@pytest.mark.parametrize("zone", ["America/Chicago", "America/New_York", "America/Los_Angeles"])
def test_targets_in_the_repeated_hour_are_never_in_the_past(target: time, zone: str) -> None:
    tz = ZoneInfo(zone)
    start = datetime(2026, 11, 1, 4, 0, tzinfo=UTC)
    for minutes in range(0, 6 * 60, 7):
        at = start + timedelta(minutes=minutes)
        release = next_local_time(at, tz, target)
        assert release >= at
        assert release.astimezone(tz).time() == target
        assert release - at < timedelta(hours=26)


def test_second_pass_of_repeated_hour_returns_the_later_instant() -> None:
    tz = ZoneInfo("America/Chicago")
    at = datetime(2026, 11, 1, 7, 15, tzinfo=UTC)  # 1:15 AM CST, after 1:30 AM CDT passed
    assert next_local_time(at, tz, time(1, 30)) == datetime(2026, 11, 1, 7, 30, tzinfo=UTC)
