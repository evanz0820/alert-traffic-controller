"""Glue between stored data and the pure engine: builds requests and profiles."""

from collections.abc import Iterable, Mapping

from atc.domain import REQUESTED_CHANNEL_BY_EVENT, Channel, priority_of
from atc.engine.types import AlertRequest, CustomerProfile
from atc.simulator.models import SimCustomer, SimEvent


def alert_id_for(event_id: int) -> str:
    return f"A-{event_id:06d}"


def build_requests(events: Iterable[tuple[int, SimEvent]]) -> list[AlertRequest]:
    """Every event produces exactly one alert request."""
    return [
        AlertRequest(
            alert_id=alert_id_for(event_id),
            event_id=event_id,
            source_id=e.source_id,
            customer_id=e.customer_id,
            account_id=e.account_id,
            event_type=e.event_type,
            priority=priority_of(e.event_type),
            requested_channel=REQUESTED_CHANNEL_BY_EVENT[e.event_type],
            requested_at=e.occurred_at,
            amount=e.amount,
        )
        for event_id, e in events
    ]


def build_profiles(customers: Iterable[SimCustomer]) -> Mapping[int, CustomerProfile]:
    profiles: dict[int, CustomerProfile] = {}
    for c in customers:
        enabled = {
            ch
            for ch, on in (
                (Channel.PUSH, c.push_enabled),
                (Channel.EMAIL, c.email_enabled),
                (Channel.SMS, c.sms_enabled),
            )
            if on
        }
        profiles[c.id] = CustomerProfile(c.id, c.timezone, c.engagement, frozenset(enabled))
    return profiles
