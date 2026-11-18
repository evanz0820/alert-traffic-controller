"""Factories for engine unit tests. Import them directly from this module."""

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

import pytest

from atc.config import RulesConfig
from atc.domain import Channel, Engagement, EventType, priority_of
from atc.engine.types import AlertRequest, CustomerContext, CustomerProfile, Delivery

BASE_TIME = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
ALL_CHANNELS = frozenset(Channel)


def make_request(**overrides: Any) -> AlertRequest:
    event_type = overrides.get("event_type", EventType.LARGE_TRANSACTION)
    fields: dict[str, Any] = {
        "alert_id": "A-0001",
        "event_id": 1,
        "source_id": "SRC-0001",
        "customer_id": 1,
        "account_id": 10,
        "event_type": event_type,
        "priority": priority_of(event_type),
        "requested_channel": Channel.PUSH,
        "requested_at": BASE_TIME,
        "amount": 500.0,
    }
    fields.update(overrides)
    return AlertRequest(**fields)


def make_profile(**overrides: Any) -> CustomerProfile:
    fields: dict[str, Any] = {
        "id": 1,
        "timezone": "America/New_York",
        "engagement": Engagement.HIGH,
        "enabled_channels": ALL_CHANNELS,
    }
    fields.update(overrides)
    return CustomerProfile(**fields)


def ctx(
    profile: CustomerProfile | None = None,
    deliveries: Iterable[Delivery] = (),
    seen_sources: Mapping[str, str] | None = None,
    fatigue_score: float = 0.0,
) -> CustomerContext:
    return CustomerContext(
        profile=profile or make_profile(),
        deliveries=tuple(deliveries),
        seen_sources=MappingProxyType(dict(seen_sources or {})),
        fatigue_score=fatigue_score,
    )


@pytest.fixture
def config() -> RulesConfig:
    return RulesConfig()
