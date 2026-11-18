from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from atc.config import DEFAULT_ORDER, RuleName, RulesConfig
from atc.domain import Channel, Engagement, EventType, Outcome, Priority
from atc.engine.pipeline import build_pipeline
from atc.engine.rules.critical_bypass import CriticalBypass
from atc.engine.rules.dedup import Dedup
from atc.engine.rules.digest import Digest
from atc.engine.rules.fatigue_gate import FatigueGate
from atc.engine.rules.frequency_cap import FrequencyCap
from atc.engine.rules.preference import PreferenceFilter
from atc.engine.rules.quiet_hours import QuietHours
from atc.engine.rules.routing import ChannelRouting
from atc.engine.types import Action, AlertRequest, Decision, Delivery
from tests.unit.engine.conftest import BASE_TIME, ctx, make_profile, make_request

ALL_PRIORITY_EVENTS = {
    Priority.CRITICAL: EventType.FRAUD_SUSPECTED,
    Priority.HIGH: EventType.LARGE_TRANSACTION,
    Priority.LOW: EventType.DEPOSIT,
    Priority.MARKETING: EventType.MARKETING_OFFER,
}


def _req_for(priority: Priority, **overrides: Any) -> AlertRequest:
    return make_request(event_type=ALL_PRIORITY_EVENTS[priority], **overrides)


# --- CriticalBypass -------------------------------------------------------------------------


@pytest.mark.parametrize("priority", list(Priority))
def test_critical_bypass_applies_only_to_critical(priority: Priority) -> None:
    assert CriticalBypass().applies_to(_req_for(priority)) is (priority is Priority.CRITICAL)


def test_critical_bypass_sends_immediately_and_is_terminal(config: RulesConfig) -> None:
    req = _req_for(Priority.CRITICAL)
    d = CriticalBypass().apply(req, Decision.initial(req), ctx(), config)
    assert d.outcome is Outcome.SENT
    assert d.terminal
    assert d.scheduled_at == req.requested_at
    assert d.decided_by is RuleName.CRITICAL_BYPASS


def test_critical_bypass_includes_every_enabled_channel_sms_first(config: RulesConfig) -> None:
    req = _req_for(Priority.CRITICAL, requested_channel=Channel.EMAIL)
    d = CriticalBypass().apply(req, Decision.initial(req), ctx(), config)
    assert d.channels == (Channel.SMS, Channel.PUSH, Channel.EMAIL)
    assert d.channel is Channel.SMS


def test_critical_bypass_forces_sms_even_when_disabled(config: RulesConfig) -> None:
    profile = make_profile(enabled_channels=frozenset({Channel.EMAIL}))
    req = _req_for(Priority.CRITICAL)
    d = CriticalBypass().apply(req, Decision.initial(req), ctx(profile), config)
    assert d.channels == (Channel.SMS, Channel.EMAIL)


def test_critical_bypass_with_no_channels_still_sends_sms(config: RulesConfig) -> None:
    profile = make_profile(enabled_channels=frozenset())
    req = _req_for(Priority.CRITICAL)
    d = CriticalBypass().apply(req, Decision.initial(req), ctx(profile), config)
    assert d.channels == (Channel.SMS,)
    assert d.outcome is Outcome.SENT


# --- Dedup ----------------------------------------------------------------------------------


def test_dedup_first_sighting_passes(config: RulesConfig) -> None:
    req = make_request()
    initial = Decision.initial(req)
    assert Dedup().apply(req, initial, ctx(), config) == initial


def test_dedup_suppresses_retry_of_seen_source(config: RulesConfig) -> None:
    req = make_request(alert_id="A-0002", source_id="SRC-1")
    d = Dedup().apply(req, Decision.initial(req), ctx(seen_sources={"SRC-1": "A-0001"}), config)
    assert d.outcome is Outcome.SUPPRESSED
    assert d.terminal
    assert d.decided_by is RuleName.DEDUP
    assert "duplicate of alert a-0001" in d.reason.lower()
    assert d.channel is None
    assert d.channels == ()


def test_dedup_does_not_suppress_the_original_alert(config: RulesConfig) -> None:
    req = make_request(alert_id="A-0001", source_id="SRC-1")
    initial = Decision.initial(req)
    assert Dedup().apply(req, initial, ctx(seen_sources={"SRC-1": "A-0001"}), config) == initial


@pytest.mark.parametrize("priority", list(Priority))
def test_dedup_skips_critical(priority: Priority) -> None:
    assert Dedup().applies_to(_req_for(priority)) is (priority is not Priority.CRITICAL)


# --- PreferenceFilter -----------------------------------------------------------------------


def test_preference_enabled_channel_passes(config: RulesConfig) -> None:
    req = make_request()
    initial = Decision.initial(req)
    assert PreferenceFilter().apply(req, initial, ctx(), config) == initial


def test_preference_disabled_channel_reroutes_by_fallback_order(config: RulesConfig) -> None:
    profile = make_profile(enabled_channels=frozenset({Channel.SMS, Channel.EMAIL}))
    req = make_request(requested_channel=Channel.PUSH)
    d = PreferenceFilter().apply(req, Decision.initial(req), ctx(profile), config)
    assert d.outcome is Outcome.REROUTED
    assert d.channel is Channel.EMAIL
    assert d.decided_by is RuleName.PREFERENCE_FILTER
    assert not d.terminal


def test_preference_custom_fallback_order(config: RulesConfig) -> None:
    custom = config.with_overrides(
        {"rules": {"preference_filter": {"fallback_order": ["sms", "email", "push"]}}}
    )
    profile = make_profile(enabled_channels=frozenset({Channel.SMS, Channel.EMAIL}))
    req = make_request(requested_channel=Channel.PUSH)
    d = PreferenceFilter().apply(req, Decision.initial(req), ctx(profile), custom)
    assert d.channel is Channel.SMS


def test_preference_no_allowed_channel_suppresses(config: RulesConfig) -> None:
    profile = make_profile(enabled_channels=frozenset())
    req = make_request()
    d = PreferenceFilter().apply(req, Decision.initial(req), ctx(profile), config)
    assert d.outcome is Outcome.SUPPRESSED
    assert d.terminal


def test_preference_skips_critical() -> None:
    assert not PreferenceFilter().applies_to(_req_for(Priority.CRITICAL))


# --- FatigueGate ----------------------------------------------------------------------------


@pytest.mark.parametrize("priority", list(Priority))
def test_fatigue_gate_applies_only_to_marketing(priority: Priority) -> None:
    assert FatigueGate().applies_to(_req_for(priority)) is (priority is Priority.MARKETING)


def test_fatigue_gate_score_at_threshold_passes(config: RulesConfig) -> None:
    req = _req_for(Priority.MARKETING)
    initial = Decision.initial(req)
    threshold = config.rules.fatigue_gate.threshold
    assert FatigueGate().apply(req, initial, ctx(fatigue_score=threshold), config) == initial


def test_fatigue_gate_above_threshold_suppresses(config: RulesConfig) -> None:
    req = _req_for(Priority.MARKETING)
    score = config.rules.fatigue_gate.threshold + 0.1
    d = FatigueGate().apply(req, Decision.initial(req), ctx(fatigue_score=score), config)
    assert d.outcome is Outcome.SUPPRESSED
    assert d.decided_by is RuleName.FATIGUE_GATE
    assert d.terminal


def test_fatigue_gate_threshold_is_configurable(config: RulesConfig) -> None:
    strict = config.with_overrides({"rules": {"fatigue_gate": {"threshold": 20}}})
    req = _req_for(Priority.MARKETING)
    initial = Decision.initial(req)
    assert FatigueGate().apply(req, initial, ctx(fatigue_score=30), config) == initial
    d = FatigueGate().apply(req, initial, ctx(fatigue_score=30), strict)
    assert d.outcome is Outcome.SUPPRESSED


# --- QuietHours -----------------------------------------------------------------------------

# 2026-10-20 23:30 EDT (UTC-4)
LATE_EVENING_NY = datetime(2026, 10, 21, 3, 30, tzinfo=UTC)
# 2026-10-21 03:00 EDT
EARLY_MORNING_NY = datetime(2026, 10, 21, 7, 0, tzinfo=UTC)
# 2026-10-21 07:00 EDT
WAKE_UP_NY = datetime(2026, 10, 21, 11, 0, tzinfo=UTC)


def test_quiet_hours_daytime_passes(config: RulesConfig) -> None:
    req = make_request()
    initial = Decision.initial(req)
    assert QuietHours().apply(req, initial, ctx(), config) == initial


def test_quiet_hours_late_evening_delays_to_next_morning(config: RulesConfig) -> None:
    req = make_request(requested_at=LATE_EVENING_NY)
    d = QuietHours().apply(req, Decision.initial(req), ctx(), config)
    assert d.outcome is Outcome.DELAYED
    assert d.decided_by is RuleName.QUIET_HOURS
    assert d.scheduled_at == WAKE_UP_NY
    assert not d.terminal


def test_quiet_hours_after_midnight_delays_to_same_local_day(config: RulesConfig) -> None:
    req = make_request(requested_at=EARLY_MORNING_NY)
    d = QuietHours().apply(req, Decision.initial(req), ctx(), config)
    assert d.outcome is Outcome.DELAYED
    assert d.scheduled_at == WAKE_UP_NY


def test_quiet_hours_large_amount_high_is_exempt(config: RulesConfig) -> None:
    exemption = config.rules.quiet_hours.high_amount_exemption
    req = make_request(requested_at=LATE_EVENING_NY, amount=exemption)
    d = QuietHours().apply(req, Decision.initial(req), ctx(), config)
    assert d.outcome is Outcome.SENT
    assert d.scheduled_at == LATE_EVENING_NY
    assert d.trace[-1].rule is RuleName.QUIET_HOURS
    assert d.trace[-1].action is Action.PASS


def test_quiet_hours_marketing_suppressed(config: RulesConfig) -> None:
    req = _req_for(Priority.MARKETING, requested_at=LATE_EVENING_NY)
    d = QuietHours().apply(req, Decision.initial(req), ctx(), config)
    assert d.outcome is Outcome.SUPPRESSED
    assert d.terminal


def test_quiet_hours_low_delayed(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW, requested_at=LATE_EVENING_NY, amount=10_000.0)
    d = QuietHours().apply(req, Decision.initial(req), ctx(), config)
    assert d.outcome is Outcome.DELAYED
    assert d.scheduled_at == WAKE_UP_NY


def test_quiet_hours_custom_window(config: RulesConfig) -> None:
    custom = config.with_overrides(
        {"rules": {"quiet_hours": {"start": "10:00:00", "end": "12:00:00"}}}
    )
    req = make_request()
    d = QuietHours().apply(req, Decision.initial(req), ctx(), custom)
    assert d.outcome is Outcome.DELAYED
    assert d.scheduled_at == datetime(2026, 10, 20, 16, 0, tzinfo=UTC)
    late = make_request(requested_at=LATE_EVENING_NY)
    assert QuietHours().apply(late, Decision.initial(late), ctx(), custom).outcome is Outcome.SENT


def test_quiet_hours_uses_customer_timezone(config: RulesConfig) -> None:
    # 22:30 EDT in New York, 19:30 PDT in Los Angeles.
    at = datetime(2026, 10, 21, 2, 30, tzinfo=UTC)
    req = make_request(requested_at=at)
    ny = QuietHours().apply(req, Decision.initial(req), ctx(), config)
    la_profile = make_profile(timezone="America/Los_Angeles")
    la = QuietHours().apply(req, Decision.initial(req), ctx(la_profile), config)
    assert ny.outcome is Outcome.DELAYED
    assert la.outcome is Outcome.SENT


def test_quiet_hours_skips_critical() -> None:
    assert not QuietHours().applies_to(_req_for(Priority.CRITICAL))


# --- FrequencyCap ---------------------------------------------------------------------------


def _earlier_today(n: int, priority: Priority = Priority.HIGH) -> list[Delivery]:
    # 12:00, 12:05, ... UTC on 2026-10-20 (morning in New York), well outside the last hour.
    start = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
    return [Delivery(start + timedelta(minutes=5 * i), priority) for i in range(n)]


def _last_hour(n: int, priority: Priority = Priority.HIGH) -> list[Delivery]:
    return [Delivery(BASE_TIME - timedelta(minutes=10 * (i + 1)), priority) for i in range(n)]


@pytest.mark.parametrize("priority", list(Priority))
def test_frequency_cap_applies_to_low_and_marketing(priority: Priority) -> None:
    expected = priority in (Priority.LOW, Priority.MARKETING)
    assert FrequencyCap().applies_to(_req_for(priority)) is expected


def test_frequency_cap_under_cap_passes(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    initial = Decision.initial(req)
    deliveries = _earlier_today(config.rules.frequency_cap.daily_cap - 1)
    assert FrequencyCap().apply(req, initial, ctx(deliveries=deliveries), config) == initial


def test_frequency_cap_daily_cap_batches_low(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    deliveries = _earlier_today(config.rules.frequency_cap.daily_cap)
    d = FrequencyCap().apply(req, Decision.initial(req), ctx(deliveries=deliveries), config)
    assert d.outcome is Outcome.BATCHED_TO_DIGEST
    assert d.decided_by is RuleName.FREQUENCY_CAP
    assert d.scheduled_at == datetime(2026, 10, 20, 22, 0, tzinfo=UTC)
    assert "daily cap" in d.reason


def test_frequency_cap_daily_cap_suppresses_low_without_digest(config: RulesConfig) -> None:
    no_digest = config.with_overrides({"rules": {"digest": {"enabled": False}}})
    req = _req_for(Priority.LOW)
    deliveries = _earlier_today(config.rules.frequency_cap.daily_cap)
    d = FrequencyCap().apply(req, Decision.initial(req), ctx(deliveries=deliveries), no_digest)
    assert d.outcome is Outcome.SUPPRESSED


def test_frequency_cap_hourly_cap(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    deliveries = _last_hour(config.rules.frequency_cap.hourly_cap)
    d = FrequencyCap().apply(req, Decision.initial(req), ctx(deliveries=deliveries), config)
    assert d.outcome is Outcome.BATCHED_TO_DIGEST
    assert "hourly cap" in d.reason


def test_frequency_cap_hourly_cap_ignores_older_deliveries(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    initial = Decision.initial(req)
    deliveries = [Delivery(BASE_TIME - timedelta(minutes=61), Priority.HIGH)] * 2
    assert FrequencyCap().apply(req, initial, ctx(deliveries=deliveries), config) == initial


def test_frequency_cap_marketing_daily_cap(config: RulesConfig) -> None:
    req = _req_for(Priority.MARKETING)
    deliveries = _earlier_today(1, Priority.MARKETING)
    d = FrequencyCap().apply(req, Decision.initial(req), ctx(deliveries=deliveries), config)
    assert d.outcome is Outcome.SUPPRESSED
    assert "today" in d.reason


def test_frequency_cap_marketing_weekly_cap(config: RulesConfig) -> None:
    req = _req_for(Priority.MARKETING)
    deliveries = [
        Delivery(BASE_TIME - timedelta(days=2), Priority.MARKETING),
        Delivery(BASE_TIME - timedelta(days=4), Priority.MARKETING),
    ]
    d = FrequencyCap().apply(req, Decision.initial(req), ctx(deliveries=deliveries), config)
    assert d.outcome is Outcome.SUPPRESSED
    assert "7 days" in d.reason


def test_frequency_cap_marketing_weekly_window_excludes_old(config: RulesConfig) -> None:
    req = _req_for(Priority.MARKETING)
    initial = Decision.initial(req)
    deliveries = [
        Delivery(BASE_TIME - timedelta(days=8), Priority.MARKETING),
        Delivery(BASE_TIME - timedelta(days=9), Priority.MARKETING),
    ]
    assert FrequencyCap().apply(req, initial, ctx(deliveries=deliveries), config) == initial


def test_frequency_cap_marketing_over_general_cap_suppressed(config: RulesConfig) -> None:
    req = _req_for(Priority.MARKETING)
    deliveries = _earlier_today(config.rules.frequency_cap.daily_cap)
    d = FrequencyCap().apply(req, Decision.initial(req), ctx(deliveries=deliveries), config)
    assert d.outcome is Outcome.SUPPRESSED


def test_frequency_cap_ignores_critical_deliveries(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    initial = Decision.initial(req)
    deliveries = _earlier_today(20, Priority.CRITICAL) + _last_hour(5, Priority.CRITICAL)
    assert FrequencyCap().apply(req, initial, ctx(deliveries=deliveries), config) == initial


def test_frequency_cap_counts_high_deliveries(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    deliveries = _last_hour(2, Priority.HIGH)
    d = FrequencyCap().apply(req, Decision.initial(req), ctx(deliveries=deliveries), config)
    assert d.outcome is Outcome.BATCHED_TO_DIGEST


# --- Digest ---------------------------------------------------------------------------------


def test_digest_batches_digestible_event_to_next_send_time(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    d = Digest().apply(req, Decision.initial(req), ctx(), config)
    assert d.outcome is Outcome.BATCHED_TO_DIGEST
    assert d.decided_by is RuleName.DIGEST
    assert d.terminal
    assert d.scheduled_at == datetime(2026, 10, 20, 22, 0, tzinfo=UTC)


def test_digest_after_send_time_rolls_to_next_day(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW, requested_at=datetime(2026, 10, 20, 23, 0, tzinfo=UTC))
    d = Digest().apply(req, Decision.initial(req), ctx(), config)
    assert d.scheduled_at == datetime(2026, 10, 21, 22, 0, tzinfo=UTC)


def test_digest_uses_customer_timezone(config: RulesConfig) -> None:
    req = _req_for(Priority.LOW)
    profile = make_profile(timezone="America/Los_Angeles")
    d = Digest().apply(req, Decision.initial(req), ctx(profile), config)
    assert d.scheduled_at == datetime(2026, 10, 21, 1, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "event_type",
    [EventType.LARGE_TRANSACTION, EventType.LOW_BALANCE, EventType.MARKETING_OFFER],
)
def test_digest_non_digestible_passes(config: RulesConfig, event_type: EventType) -> None:
    req = make_request(event_type=event_type)
    initial = Decision.initial(req)
    assert Digest().apply(req, initial, ctx(), config) == initial


def test_digest_event_types_configurable(config: RulesConfig) -> None:
    custom = config.with_overrides({"rules": {"digest": {"event_types": ["statement_ready"]}}})
    deposit = make_request(event_type=EventType.DEPOSIT)
    statement = make_request(event_type=EventType.STATEMENT_READY)
    assert Digest().apply(deposit, Decision.initial(deposit), ctx(), custom).outcome is (
        Outcome.SENT
    )
    d = Digest().apply(statement, Decision.initial(statement), ctx(), custom)
    assert d.outcome is Outcome.BATCHED_TO_DIGEST


# --- ChannelRouting -------------------------------------------------------------------------


def _open_probability(config: RulesConfig, value: float) -> RulesConfig:
    probabilities = {e.value: value for e in Engagement}
    overrides: dict[str, object] = {
        "rules": {"channel_routing": {"open_probability": probabilities}}
    }
    return config.with_overrides(overrides)


def test_routing_high_engagement_push_opened(config: RulesConfig) -> None:
    always = _open_probability(config, 1.0)
    req = make_request(requested_channel=Channel.EMAIL)
    d = ChannelRouting().apply(req, Decision.initial(req), ctx(), always)
    assert d.channel is Channel.PUSH
    assert d.channels == (Channel.PUSH,)
    assert d.outcome is Outcome.REROUTED


def test_routing_keeps_requested_push_unchanged_when_opened(config: RulesConfig) -> None:
    always = _open_probability(config, 1.0)
    req = make_request(requested_channel=Channel.PUSH)
    d = ChannelRouting().apply(req, Decision.initial(req), ctx(), always)
    assert d.outcome is Outcome.SENT
    assert d.channels == (Channel.PUSH,)
    assert d.decided_by is None


def test_routing_low_engagement_reroutes_to_email(config: RulesConfig) -> None:
    profile = make_profile(engagement=Engagement.LOW)
    req = make_request(requested_channel=Channel.PUSH)
    d = ChannelRouting().apply(req, Decision.initial(req), ctx(profile), config)
    assert d.outcome is Outcome.REROUTED
    assert d.channel is Channel.EMAIL
    assert d.channels == (Channel.EMAIL,)
    assert d.decided_by is RuleName.CHANNEL_ROUTING


def test_routing_respects_disabled_channels(config: RulesConfig) -> None:
    profile = make_profile(enabled_channels=frozenset({Channel.EMAIL, Channel.SMS}))
    req = make_request(requested_channel=Channel.EMAIL)
    d = ChannelRouting().apply(req, Decision.initial(req), ctx(profile), config)
    assert d.channel is Channel.EMAIL
    assert d.channels == (Channel.EMAIL,)
    assert Channel.PUSH not in d.channels


def test_routing_push_not_opened_falls_back_to_email(config: RulesConfig) -> None:
    never = _open_probability(config, 0.0)
    req = make_request(requested_channel=Channel.PUSH)
    d = ChannelRouting().apply(req, Decision.initial(req), ctx(), never)
    assert d.channels == (Channel.PUSH, Channel.EMAIL)
    assert d.channel is Channel.EMAIL
    assert d.outcome is Outcome.REROUTED
    assert d.trace[-1].action is Action.FALLBACK


def test_routing_no_fallback_when_email_disabled(config: RulesConfig) -> None:
    never = _open_probability(config, 0.0)
    profile = make_profile(enabled_channels=frozenset({Channel.PUSH}))
    req = make_request(requested_channel=Channel.PUSH)
    d = ChannelRouting().apply(req, Decision.initial(req), ctx(profile), never)
    assert d.channels == (Channel.PUSH,)


def test_routing_delayed_decision_stays_delayed_after_fallback(config: RulesConfig) -> None:
    never = _open_probability(config, 0.0)
    req = make_request(requested_at=LATE_EVENING_NY)
    delayed = QuietHours().apply(req, Decision.initial(req), ctx(), never)
    d = ChannelRouting().apply(req, delayed, ctx(), never)
    assert d.outcome is Outcome.DELAYED
    assert d.decided_by is RuleName.QUIET_HOURS
    assert d.scheduled_at == WAKE_UP_NY
    assert d.channels == (Channel.PUSH, Channel.EMAIL)


def test_routing_delayed_decision_stays_delayed_after_reroute(config: RulesConfig) -> None:
    profile = make_profile(engagement=Engagement.LOW)
    req = make_request(requested_at=LATE_EVENING_NY)
    delayed = QuietHours().apply(req, Decision.initial(req), ctx(profile), config)
    d = ChannelRouting().apply(req, delayed, ctx(profile), config)
    assert d.outcome is Outcome.DELAYED
    assert d.channel is Channel.EMAIL


def test_routing_skips_critical() -> None:
    assert not ChannelRouting().applies_to(_req_for(Priority.CRITICAL))


# --- build_pipeline -------------------------------------------------------------------------


def test_build_pipeline_default_order(config: RulesConfig) -> None:
    assert tuple(r.name for r in build_pipeline(config)) == DEFAULT_ORDER


def test_config_rejects_critical_bypass_not_first() -> None:
    with pytest.raises(ValidationError):
        RulesConfig(pipeline=(RuleName.DEDUP, RuleName.CRITICAL_BYPASS, *DEFAULT_ORDER[2:]))


def test_config_rejects_missing_critical_bypass() -> None:
    with pytest.raises(ValidationError):
        RulesConfig(pipeline=DEFAULT_ORDER[1:])


def test_config_rejects_duplicate_rules() -> None:
    with pytest.raises(ValidationError):
        RulesConfig(pipeline=(*DEFAULT_ORDER, RuleName.DEDUP))


def test_build_pipeline_disabling_rule_removes_it(config: RulesConfig) -> None:
    custom = config.with_overrides({"rules": {"quiet_hours": {"enabled": False}}})
    names = [r.name for r in build_pipeline(custom)]
    assert RuleName.QUIET_HOURS not in names
    assert len(names) == len(DEFAULT_ORDER) - 1


def test_build_pipeline_critical_bypass_cannot_be_disabled(config: RulesConfig) -> None:
    with pytest.raises(ValidationError):
        config.with_overrides({"rules": {"critical_bypass": {"enabled": False}}})


def test_build_pipeline_honors_reordering() -> None:
    order = (
        RuleName.CRITICAL_BYPASS,
        RuleName.CHANNEL_ROUTING,
        RuleName.DIGEST,
        RuleName.DEDUP,
        RuleName.PREFERENCE_FILTER,
        RuleName.FATIGUE_GATE,
        RuleName.QUIET_HOURS,
        RuleName.FREQUENCY_CAP,
    )
    config = RulesConfig(pipeline=order)
    assert tuple(r.name for r in build_pipeline(config)) == order


# --- Config ---------------------------------------------------------------------------------


def test_with_overrides_deep_merges(config: RulesConfig) -> None:
    custom = config.with_overrides(
        {
            "rules": {
                "frequency_cap": {"daily_cap": 9},
                "channel_routing": {"open_probability": {"low": 0.1}},
            }
        }
    )
    assert custom.rules.frequency_cap.daily_cap == 9
    assert custom.rules.frequency_cap.hourly_cap == config.rules.frequency_cap.hourly_cap
    probs = custom.rules.channel_routing.open_probability
    assert probs[Engagement.LOW] == 0.1
    assert probs[Engagement.HIGH] == config.rules.channel_routing.open_probability[Engagement.HIGH]
    assert custom.rules.quiet_hours == config.rules.quiet_hours
    assert custom.pipeline == config.pipeline


def test_with_overrides_does_not_mutate_original(config: RulesConfig) -> None:
    config.with_overrides({"rules": {"frequency_cap": {"daily_cap": 9}}})
    assert config.rules.frequency_cap.daily_cap == 5


@pytest.mark.parametrize(
    "overrides",
    [
        {"rules": {"frequency_cap": {"daily_cap": 0}}},
        {"rules": {"fatigue_gate": {"threshold": 101}}},
        {"rules": {"digest": {"event_types": ["deposit", "large_transaction"]}}},
        {"rules": {"digest": {"event_types": ["fraud_suspected"]}}},
        {"rules": {"dedup": {"unknown_knob": True}}},
    ],
)
def test_with_overrides_rejects_invalid_values(
    config: RulesConfig, overrides: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        config.with_overrides(overrides)
