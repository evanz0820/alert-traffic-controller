"""THE guarantee: for any event stream and any valid config, every critical alert is sent,
instantly, on SMS plus every enabled channel. Never weaken or skip this test."""

from datetime import timedelta

from hypothesis import HealthCheck, given, settings

from atc.config import RulesConfig
from atc.domain import Channel, Outcome, Priority
from atc.engine.pipeline import run_controller
from atc.engine.types import AlertRequest, CustomerProfile
from tests.property.strategies import configs, streams

Stream = tuple[list[AlertRequest], dict[int, CustomerProfile]]
SETTINGS = settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@SETTINGS
@given(stream=streams(), config=configs())
def test_critical_requested_equals_critical_sent(stream: Stream, config: RulesConfig) -> None:
    requests, people = stream
    result = run_controller(requests, people, config)

    requested = [r for r in requests if r.priority is Priority.CRITICAL]
    sent = [
        r
        for r in result.results
        if r.request.priority is Priority.CRITICAL and r.decision.outcome is Outcome.SENT
    ]
    assert len(sent) == len(requested)


@SETTINGS
@given(stream=streams(), config=configs())
def test_no_critical_alert_is_ever_delayed(stream: Stream, config: RulesConfig) -> None:
    requests, people = stream
    for r in run_controller(requests, people, config).results:
        if r.request.priority is not Priority.CRITICAL:
            continue
        assert r.decision.outcome is Outcome.SENT
        assert r.decision.scheduled_at == r.request.requested_at
        assert r.delivered_at is not None
        assert r.delivered_at - r.request.requested_at < timedelta(seconds=5)
        assert r.digest_index is None


@SETTINGS
@given(stream=streams(), config=configs())
def test_critical_uses_sms_and_all_enabled_channels(stream: Stream, config: RulesConfig) -> None:
    requests, people = stream
    for r in run_controller(requests, people, config).results:
        if r.request.priority is Priority.CRITICAL:
            enabled = people[r.request.customer_id].enabled_channels
            assert set(r.decision.channels) == enabled | {Channel.SMS}


@SETTINGS
@given(stream=streams(), config=configs())
def test_every_request_gets_exactly_one_decision(stream: Stream, config: RulesConfig) -> None:
    requests, people = stream
    result = run_controller(requests, people, config)
    assert sorted(r.request.alert_id for r in result.results) == sorted(
        r.alert_id for r in requests
    )
    for r in result.results:
        assert r.decision.decided_by is not None or r.decision.outcome is Outcome.SENT
        if r.decision.outcome is not Outcome.SUPPRESSED:
            assert r.delivered_at is not None and r.delivered_at >= r.request.requested_at


@SETTINGS
@given(stream=streams(), config=configs())
def test_non_critical_never_uses_a_disabled_channel(stream: Stream, config: RulesConfig) -> None:
    requests, people = stream
    if not config.rules.preference_filter.enabled and not config.rules.channel_routing.enabled:
        return
    for r in run_controller(requests, people, config).results:
        if r.request.priority is Priority.CRITICAL or r.decision.outcome is Outcome.SUPPRESSED:
            continue
        if r.decision.outcome is Outcome.BATCHED_TO_DIGEST:
            continue
        enabled = people[r.request.customer_id].enabled_channels
        if config.rules.preference_filter.enabled and enabled:
            assert set(r.decision.channels) <= enabled
