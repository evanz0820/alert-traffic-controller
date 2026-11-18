"""Dedup is idempotent: retries never change the fate of the original alert, and running
the controller over an already-deduplicated stream suppresses nothing as a duplicate."""

from hypothesis import given, settings

from atc.config import RuleName, RulesConfig
from atc.domain import Outcome, Priority
from atc.engine.pipeline import run_controller
from atc.engine.types import AlertRequest, CustomerProfile
from tests.property.strategies import streams

Stream = tuple[list[AlertRequest], dict[int, CustomerProfile]]
CONFIG = RulesConfig()


@settings(max_examples=200, deadline=None)
@given(stream=streams())
def test_dedup_applied_twice_changes_nothing(stream: Stream) -> None:
    requests, people = stream
    first = run_controller(requests, people, CONFIG)
    survivors = {
        r.request.alert_id for r in first.results if r.decision.decided_by is not RuleName.DEDUP
    }
    second = run_controller([r for r in requests if r.alert_id in survivors], people, CONFIG)
    assert all(r.decision.decided_by is not RuleName.DEDUP for r in second.results)


@settings(max_examples=200, deadline=None)
@given(stream=streams())
def test_retries_do_not_change_original_decisions(stream: Stream) -> None:
    requests, people = stream
    seen: set[str] = set()
    originals: list[AlertRequest] = []
    for r in sorted(requests, key=lambda r: (r.requested_at, r.event_id)):
        if r.source_id not in seen:
            seen.add(r.source_id)
            originals.append(r)

    with_retries = {r.request.alert_id: r for r in run_controller(requests, people, CONFIG).results}
    without = {r.request.alert_id: r for r in run_controller(originals, people, CONFIG).results}
    for alert_id, result in without.items():
        assert with_retries[alert_id].decision == result.decision

    for alert_id, result in with_retries.items():
        if alert_id in without:
            continue
        if result.request.priority is Priority.CRITICAL:
            # Critical retries are sent again by design: never risk deduping a real alert.
            assert result.decision.outcome is Outcome.SENT
        else:
            assert result.decision.outcome is Outcome.SUPPRESSED
            assert result.decision.decided_by is RuleName.DEDUP


@settings(max_examples=50, deadline=None)
@given(stream=streams())
def test_running_twice_is_deterministic(stream: Stream) -> None:
    requests, people = stream
    assert run_controller(requests, people, CONFIG) == run_controller(requests, people, CONFIG)
