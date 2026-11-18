"""Timezone helpers. Wall-clock math happens in the customer's zone via zoneinfo, so
DST transitions are handled by the tz database rather than fixed offsets."""

import hashlib
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo


def in_window(t: time, start: time, end: time) -> bool:
    """True if local time `t` falls in [start, end); windows may wrap past midnight."""
    if start <= end:
        return start <= t < end
    return t >= start or t < end


def next_local_time(at: datetime, tz: ZoneInfo, target: time) -> datetime:
    """The first instant at or after `at` whose local wall-clock time is `target`, in UTC."""
    local = at.astimezone(tz)
    for offset in (0, 1):
        day = local.date() + timedelta(days=offset)
        # A wall-clock time can occur twice on a fall-back day (fold 0 then fold 1).
        for fold in (0, 1):
            candidate = datetime.combine(day, target, tzinfo=tz).replace(fold=fold)
            instant = candidate.astimezone(UTC)
            if instant >= at:
                return instant
    raise AssertionError(
        "unreachable: a wall-clock time recurs within two days"
    )  # pragma: no cover


def format_local(at: datetime, tz: ZoneInfo) -> str:
    """'11:42 PM CST' style label for explanations."""
    local = at.astimezone(tz)
    return f"{local:%I:%M %p}".lstrip("0") + f" {local:%Z}"


def format_clock(t: time) -> str:
    return f"{datetime.combine(datetime.min, t):%I:%M %p}".lstrip("0")


def stable_unit(*parts: object) -> float:
    """Deterministic pseudo-random number in [0, 1) derived from its inputs."""
    digest = hashlib.blake2b(":".join(map(str, parts)).encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64
