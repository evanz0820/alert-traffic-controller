"""Hypothesis strategies for random alert streams and random rule configurations."""

from datetime import UTC, datetime, timedelta

from hypothesis import strategies as st

from atc.config import RuleName, RulesConfig
from atc.domain import (
    REQUESTED_CHANNEL_BY_EVENT,
    Channel,
    Engagement,
    EventType,
    priority_of,
)
from atc.engine.types import AlertRequest, CustomerProfile

ZONES = (
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Phoenix",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
)
# Window spans the US fall-back (Nov 1, 2026) so DST is exercised.
START = datetime(2026, 10, 28, tzinfo=UTC)
SPAN_SECONDS = int(timedelta(days=8).total_seconds())


@st.composite
def profiles(draw: st.DrawFn, count: int) -> dict[int, CustomerProfile]:
    out: dict[int, CustomerProfile] = {}
    for cid in range(1, count + 1):
        channels = draw(st.frozensets(st.sampled_from(list(Channel))))
        out[cid] = CustomerProfile(
            id=cid,
            timezone=draw(st.sampled_from(ZONES)),
            engagement=draw(st.sampled_from(list(Engagement))),
            enabled_channels=channels,
        )
    return out


@st.composite
def streams(draw: st.DrawFn) -> tuple[list[AlertRequest], dict[int, CustomerProfile]]:
    """A random event stream including bursts and upstream retries (reused source ids)."""
    customers = draw(st.integers(min_value=1, max_value=6))
    people = draw(profiles(customers))
    n = draw(st.integers(min_value=1, max_value=120))
    requests: list[AlertRequest] = []
    for i in range(1, n + 1):
        event_type = draw(st.sampled_from(list(EventType)))
        if requests and draw(st.integers(0, 9)) == 0:
            # Retry of an earlier event: same source id and customer, a bit later.
            original = draw(st.sampled_from(requests))
            requests.append(
                AlertRequest(
                    alert_id=f"A-{i:06d}",
                    event_id=i,
                    source_id=original.source_id,
                    customer_id=original.customer_id,
                    account_id=original.account_id,
                    event_type=original.event_type,
                    priority=original.priority,
                    requested_channel=original.requested_channel,
                    requested_at=original.requested_at
                    + timedelta(seconds=draw(st.integers(1, 600))),
                    amount=original.amount,
                )
            )
            continue
        requests.append(
            AlertRequest(
                alert_id=f"A-{i:06d}",
                event_id=i,
                source_id=f"src-{i:06d}",
                customer_id=draw(st.integers(1, customers)),
                account_id=1,
                event_type=event_type,
                priority=priority_of(event_type),
                requested_channel=REQUESTED_CHANNEL_BY_EVENT[event_type],
                requested_at=START + timedelta(seconds=draw(st.integers(0, SPAN_SECONDS))),
                amount=draw(st.none() | st.floats(min_value=1, max_value=20_000)),
            )
        )
    return requests, people


@st.composite
def configs(draw: st.DrawFn) -> RulesConfig:
    """Any valid configuration: rules toggled, reordered, and re-tuned."""
    movable = [r for r in RuleName if r is not RuleName.CRITICAL_BYPASS]
    order = draw(st.permutations(movable))
    toggles = {r.value: {"enabled": draw(st.booleans())} for r in movable}
    overrides: dict[str, object] = {
        "pipeline": [RuleName.CRITICAL_BYPASS.value, *[r.value for r in order]],
        "rules": {
            **toggles,
            "frequency_cap": {
                **toggles["frequency_cap"],
                "daily_cap": draw(st.integers(1, 10)),
                "hourly_cap": draw(st.integers(1, 5)),
                "marketing_daily_cap": draw(st.integers(0, 3)),
                "marketing_weekly_cap": draw(st.integers(0, 5)),
            },
            "fatigue_gate": {
                **toggles["fatigue_gate"],
                "threshold": draw(st.floats(min_value=0, max_value=100)),
            },
            "quiet_hours": {
                **toggles["quiet_hours"],
                "start": f"{draw(st.integers(18, 23)):02d}:00",
                "end": f"{draw(st.integers(5, 9)):02d}:00",
            },
            "digest": {**toggles["digest"], "send_at": f"{draw(st.integers(6, 21)):02d}:30"},
        },
    }
    return RulesConfig().with_overrides(overrides)
