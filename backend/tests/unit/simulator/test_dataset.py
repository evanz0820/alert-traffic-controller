from collections import Counter
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from atc.domain import AccountType, EventType, Priority, priority_of
from atc.simulator.dataset import build_dataset
from atc.simulator.events import CAMPAIGN_SPREAD_MINUTES, CAMPAIGNS
from atc.simulator.models import Dataset


def test_same_seed_is_deterministic(dataset: Dataset) -> None:
    assert build_dataset() == dataset


def test_different_seed_differs(dataset: Dataset) -> None:
    other = build_dataset(seed=7)
    assert other.customers != dataset.customers
    assert other.events != dataset.events


def test_customer_population(dataset: Dataset) -> None:
    assert len(dataset.customers) == 500
    assert len({c.timezone for c in dataset.customers}) >= 6
    assert {c.segment for c in dataset.customers} == {"mass", "mass_affluent", "senior"}
    assert {c.engagement for c in dataset.customers} == {"high", "medium", "low"}


def test_channel_preferences_have_opt_outs(dataset: Dataset) -> None:
    customers = dataset.customers
    assert any(not c.push_enabled for c in customers)
    assert any(not c.email_enabled for c in customers)
    assert any(not c.sms_enabled for c in customers)
    assert all(c.push_enabled or c.email_enabled for c in customers)


def test_accounts_one_to_three_with_checking(dataset: Dataset) -> None:
    per_customer: dict[int, list[AccountType]] = {}
    for a in dataset.accounts:
        per_customer.setdefault(a.customer_id, []).append(a.account_type)
    assert set(per_customer) == {c.id for c in dataset.customers}
    for types in per_customer.values():
        assert 1 <= len(types) <= 3
        assert types.count(AccountType.CHECKING) == 1
        assert len(set(types)) == len(types)


def test_cobrand_accounts_have_partners_and_others_do_not(dataset: Dataset) -> None:
    cobrand = [a for a in dataset.accounts if a.account_type is AccountType.COBRAND_CARD]
    assert cobrand, "expected some cobrand cards"
    assert {a.partner_code for a in cobrand} == {"AARP", "SUMMIT", "HARVEST"}
    others = [a for a in dataset.accounts if a.account_type is not AccountType.COBRAND_CARD]
    assert all(a.partner_code is None for a in others)


def test_events_are_sorted_utc_and_inside_window(dataset: Dataset) -> None:
    start = datetime.combine(dataset.start, datetime.min.time(), tzinfo=UTC)
    end = start + timedelta(days=dataset.days)
    times = [e.occurred_at for e in dataset.events]
    assert times == sorted(times)
    assert all(t.tzinfo is UTC for t in times)
    assert start <= times[0] and times[-1] < end


def test_events_reference_the_customers_own_account(dataset: Dataset) -> None:
    owner = {a.id: a.customer_id for a in dataset.accounts}
    assert all(owner[e.account_id] == e.customer_id for e in dataset.events)


def test_every_event_type_occurs(dataset: Dataset) -> None:
    assert {e.event_type for e in dataset.events} == set(EventType)


def test_realistic_frequency(dataset: Dataset) -> None:
    counts = Counter(priority_of(e.event_type) for e in dataset.events)
    total = len(dataset.events)
    assert 10_000 < total < 25_000
    assert counts[Priority.CRITICAL] / total < 0.02
    by_type = Counter(e.event_type for e in dataset.events)
    common = by_type[EventType.LARGE_TRANSACTION] + by_type[EventType.DEPOSIT]
    assert common / total > 0.5
    assert by_type[EventType.FRAUD_SUSPECTED] < by_type[EventType.DEPOSIT] / 20


def test_about_five_percent_are_retries_of_earlier_events(dataset: Dataset) -> None:
    retries = [e for e in dataset.events if e.is_retry]
    assert 0.035 < len(retries) / len(dataset.events) < 0.07
    first_seen: dict[str, datetime] = {}
    for e in dataset.events:
        if not e.is_retry:
            first_seen.setdefault(e.source_id, e.occurred_at)
    for r in retries:
        # Retries of events near the window start may have an original outside it.
        if r.source_id in first_seen:
            assert first_seen[r.source_id] < r.occurred_at


def test_source_ids_unique_among_originals(dataset: Dataset) -> None:
    originals = [e.source_id for e in dataset.events if not e.is_retry]
    assert len(originals) == len(set(originals))


def test_marketing_arrives_in_campaign_bursts(dataset: Dataset) -> None:
    marketing = [e for e in dataset.events if e.event_type is EventType.MARKETING_OFFER]
    campaign_ids = {c.id for c in CAMPAIGNS}
    in_campaign = [e for e in marketing if e.campaign_id in campaign_ids]
    assert len(in_campaign) / len(marketing) > 0.8
    for campaign in CAMPAIGNS:
        sends = sorted(e.occurred_at for e in in_campaign if e.campaign_id == campaign.id)
        assert sends[-1] - sends[0] <= timedelta(minutes=CAMPAIGN_SPREAD_MINUTES + 4)


def test_some_events_arrive_overnight_local_time(dataset: Dataset) -> None:
    tz = {c.id: ZoneInfo(c.timezone) for c in dataset.customers}
    night = sum(
        1 for e in dataset.events if not 7 <= e.occurred_at.astimezone(tz[e.customer_id]).hour < 22
    )
    assert night / len(dataset.events) > 0.10


def test_transaction_bursts_within_minutes(dataset: Dataset) -> None:
    last: dict[int, datetime] = {}
    tight = 0
    for e in dataset.events:
        if e.event_type is EventType.LARGE_TRANSACTION and not e.is_retry:
            prev = last.get(e.customer_id)
            if prev and e.occurred_at - prev <= timedelta(minutes=5):
                tight += 1
            last[e.customer_id] = e.occurred_at
    assert tight > 50
