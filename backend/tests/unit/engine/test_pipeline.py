from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from atc.config import RulesConfig, load_config, save_config
from atc.domain import Channel, EventType, Outcome, Priority
from atc.engine.pipeline import (
    CriticalGuaranteeError,
    _guard_critical,
    run_baseline,
    run_controller,
)
from atc.engine.types import Decision
from tests.unit.engine.conftest import BASE_TIME, make_profile, make_request


def test_baseline_sends_everything_as_requested() -> None:
    profiles = {1: make_profile(enabled_channels=frozenset({Channel.EMAIL}))}
    requests = [
        make_request(alert_id="A-1", event_id=1, source_id="s1"),
        make_request(alert_id="A-2", event_id=2, source_id="s1"),  # retry: still sent
        make_request(
            alert_id="A-3", event_id=3, source_id="s3", event_type=EventType.MARKETING_OFFER
        ),
    ]
    result = run_baseline(requests, profiles, RulesConfig())
    assert [r.decision.outcome for r in result.results] == [Outcome.SENT] * 3
    assert all(r.decision.channel is r.request.requested_channel for r in result.results)
    assert result.digests == ()
    assert result.fatigue[1].delivered == 3


def test_controller_beats_baseline_on_volume() -> None:
    profiles = {1: make_profile()}
    requests = [
        make_request(
            alert_id=f"A-{i}",
            event_id=i,
            source_id=f"s{i}",
            event_type=EventType.DEPOSIT,
            requested_at=BASE_TIME + timedelta(minutes=10 * i),
        )
        for i in range(1, 6)
    ]
    atc = run_controller(requests, profiles, RulesConfig())
    assert len(atc.digests) == 1
    assert len(atc.digests[0].alert_ids) == 5
    assert (
        atc.fatigue[1].delivered
        < run_baseline(requests, profiles, RulesConfig()).fatigue[1].delivered
    )


def test_empty_stream() -> None:
    result = run_controller([], {}, RulesConfig())
    assert result.results == () and result.digests == () and dict(result.fatigue) == {}


def test_guard_rejects_a_delayed_critical_alert() -> None:
    req = make_request(event_type=EventType.FRAUD_SUSPECTED)
    assert req.priority is Priority.CRITICAL
    held = replace(
        Decision.initial(req),
        outcome=Outcome.DELAYED,
        scheduled_at=req.requested_at + timedelta(hours=1),
        channels=(Channel.SMS,),
    )
    with pytest.raises(CriticalGuaranteeError):
        _guard_critical(req, held, make_profile())


def test_guard_rejects_critical_without_sms() -> None:
    req = make_request(event_type=EventType.CARD_LOCKED)
    no_sms = replace(Decision.initial(req), channels=(Channel.PUSH,))
    with pytest.raises(CriticalGuaranteeError):
        _guard_critical(req, no_sms, make_profile())


def test_config_round_trips_through_yaml(tmp_path: Path) -> None:
    path = tmp_path / "rules.yaml"
    custom = RulesConfig().with_overrides({"rules": {"frequency_cap": {"daily_cap": 9}}})
    save_config(custom, path)
    assert "daily_cap: 9" in path.read_text()
    assert load_config(path) == custom


def test_missing_config_file_falls_back_to_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path / "nope.yaml") == RulesConfig()


def test_guard_rejects_critical_missing_an_enabled_channel() -> None:
    req = make_request(event_type=EventType.FRAUD_SUSPECTED)
    sms_only = replace(Decision.initial(req), channels=(Channel.SMS,))
    with pytest.raises(CriticalGuaranteeError):
        _guard_critical(req, sms_only, make_profile())  # push and email are on


def test_priority_must_match_event_type() -> None:
    with pytest.raises(ValueError, match="must have priority critical"):
        make_request(event_type=EventType.FRAUD_SUSPECTED, priority=Priority.LOW)


def test_requested_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        make_request(requested_at=BASE_TIME.replace(tzinfo=None))


def test_digest_never_uses_a_disabled_channel() -> None:
    profiles = {1: make_profile(enabled_channels=frozenset({Channel.SMS}))}
    requests = [
        make_request(alert_id="A-1", event_id=1, source_id="s1", event_type=EventType.DEPOSIT)
    ]
    result = run_controller(requests, profiles, RulesConfig())
    assert result.digests[0].channel is Channel.SMS


def test_unreachable_customer_is_not_batched() -> None:
    profiles = {1: make_profile(enabled_channels=frozenset())}
    config = RulesConfig().with_overrides({"rules": {"preference_filter": {"enabled": False}}})
    requests = [
        make_request(alert_id="A-1", event_id=1, source_id="s1", event_type=EventType.DEPOSIT)
    ]
    result = run_controller(requests, profiles, config)
    assert result.digests == ()
    assert result.results[0].decision.outcome is Outcome.SUPPRESSED
