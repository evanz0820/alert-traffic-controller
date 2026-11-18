"""Synthetic event stream: 30 days of upstream alert triggers, messiness included.

Upstream producers fire independently, so the stream deliberately contains what real
banks see: nightly batch jobs posting at 3 AM local time, marketing campaigns blasted at
one instant regardless of each customer's time zone, shopping bursts minutes apart, and
retries that resend the same event (same source id) seconds later.
"""

import math
import random
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from atc.domain import CARD_ACCOUNT_TYPES, AccountType, EventType, Segment
from atc.simulator.models import SimAccount, SimCustomer, SimEvent

# Share of hourly activity by local hour (consumer spending / app usage curve).
DIURNAL_WEIGHTS: tuple[float, ...] = (
    0.2,
    0.1,
    0.1,
    0.1,
    0.1,
    0.2,
    0.5,
    1.2,
    2.0,
    2.5,
    2.8,
    3.0,
    3.2,
    3.0,
    2.8,
    2.7,
    2.8,
    3.0,
    3.1,
    2.9,
    2.4,
    1.8,
    1.0,
    0.5,
)

# Expected events per customer per day.
TXN_RATE: dict[Segment, float] = {
    Segment.MASS: 0.35,
    Segment.MASS_AFFLUENT: 0.50,
    Segment.SENIOR: 0.20,
}
LOW_BALANCE_RATE: dict[Segment, float] = {
    Segment.MASS: 0.08,
    Segment.MASS_AFFLUENT: 0.02,
    Segment.SENIOR: 0.04,
}
AD_HOC_DEPOSIT_RATE = 0.20
INTERNATIONAL_RATE = 0.02
FRAUD_RATE = 0.004
CARD_LOCK_RATE = 0.0015
NEW_DEVICE_RATE = 0.006
CREDIT_LIMIT_RATE_PER_CARD = 0.003
MARKETING_DRIP_RATE = 0.03

FRAUD_TRIGGERS_LOCK = 0.5
BURST_PROBABILITY = 0.04
TXN_TRIGGERS_LOW_BALANCE = 0.10
ON_TIME_PAYMENT = 0.92
RETRY_PROBABILITY = 0.05
DOUBLE_RETRY_PROBABILITY = 0.10
CAMPAIGN_SPREAD_MINUTES = 90


@dataclass(frozen=True, slots=True)
class Campaign:
    id: str
    day: int
    start_et: time  # campaigns are scheduled in Eastern time, blasted to everyone at once
    reach: float


CAMPAIGNS: tuple[Campaign, ...] = (
    Campaign("holiday-cashback", 2, time(10, 0), 0.75),
    Campaign("cashback-reminder", 4, time(18, 0), 0.50),
    Campaign("travel-card-upgrade", 11, time(21, 30), 0.65),
    Campaign("savings-rate-promo", 18, time(8, 0), 0.70),
    Campaign("early-black-friday", 25, time(6, 0), 0.80),
    Campaign("black-friday-encore", 27, time(12, 0), 0.60),
)

_EASTERN = ZoneInfo("America/New_York")


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm; fine for the small rates used here."""
    threshold, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


def _at_local(day: date, minute_of_day: float, tz: ZoneInfo) -> datetime:
    local = datetime.combine(day, time()) + timedelta(minutes=minute_of_day)
    return local.replace(tzinfo=tz, microsecond=0).astimezone(UTC)


def _diurnal_minute(rng: random.Random) -> float:
    hour = rng.choices(range(24), weights=DIURNAL_WEIGHTS, k=1)[0]
    return hour * 60 + rng.random() * 60


def _window_minute(rng: random.Random, start_hour: float, end_hour: float) -> float:
    return rng.uniform(start_hour * 60, end_hour * 60)


def _amount(rng: random.Random, median: float, sigma: float, floor: float) -> float:
    return round(max(floor, rng.lognormvariate(math.log(median), sigma)), 2)


class _EventFactory:
    """Mints events with deterministic, per-producer source ids."""

    def __init__(self) -> None:
        self._counter = 0
        self.events: list[SimEvent] = []

    def emit(
        self,
        producer: str,
        customer: SimCustomer,
        account: SimAccount,
        event_type: EventType,
        at: datetime,
        amount: float | None = None,
        campaign_id: str | None = None,
    ) -> SimEvent:
        self._counter += 1
        event = SimEvent(
            source_id=f"{producer}-{self._counter:06d}",
            customer_id=customer.id,
            account_id=account.id,
            event_type=event_type,
            occurred_at=at.replace(microsecond=0),
            amount=amount,
            campaign_id=campaign_id,
        )
        self.events.append(event)
        return event


def generate_events(
    rng: random.Random,
    customers: list[SimCustomer],
    accounts: list[SimAccount],
    start: date,
    days: int,
) -> list[SimEvent]:
    by_customer: dict[int, list[SimAccount]] = {}
    for a in accounts:
        by_customer.setdefault(a.customer_id, []).append(a)

    window_start = datetime.combine(start, time(), tzinfo=UTC)
    window_end = window_start + timedelta(days=days)
    factory = _EventFactory()

    for customer in customers:
        _customer_events(rng, factory, customer, by_customer[customer.id], start, days)
    _campaign_events(rng, factory, customers, by_customer, start)

    events = [e for e in factory.events if window_start <= e.occurred_at < window_end]
    events.extend(_inject_retries(rng, events))
    events.sort(key=lambda e: (e.occurred_at, e.source_id, e.is_retry))
    return events


def _customer_events(
    rng: random.Random,
    factory: _EventFactory,
    customer: SimCustomer,
    accounts: list[SimAccount],
    start: date,
    days: int,
) -> None:
    tz = ZoneInfo(customer.timezone)
    checking = next(a for a in accounts if a.account_type is AccountType.CHECKING)
    cards = [a for a in accounts if a.account_type in CARD_ACCOUNT_TYPES]
    spend_accounts = [checking, *cards]
    payday_phase = rng.randrange(14)

    def emit(
        producer: str,
        account: SimAccount,
        event_type: EventType,
        at: datetime,
        amount: float | None = None,
        campaign_id: str | None = None,
    ) -> SimEvent:
        return factory.emit(producer, customer, account, event_type, at, amount, campaign_id)

    for d in range(days):
        day = start + timedelta(days=d)

        def local(minute: float, day: date = day) -> datetime:
            return _at_local(day, minute, tz)

        # Deposits: biweekly payroll posts in the overnight ACH batch; seniors get a
        # monthly benefit deposit; plus ad hoc daytime deposits.
        is_payday = day.weekday() == 4 and (d + payday_phase) % 14 < 7
        if customer.segment is Segment.SENIOR:
            is_payday = day.day == 3
        if is_payday:
            emit(
                "core",
                checking,
                EventType.DEPOSIT,
                local(_window_minute(rng, 2, 5)),
                amount=_amount(rng, 2100, 0.4, 300),
            )
        for _ in range(_poisson(rng, AD_HOC_DEPOSIT_RATE)):
            emit(
                "core",
                checking,
                EventType.DEPOSIT,
                local(_diurnal_minute(rng)),
                amount=_amount(rng, 250, 0.9, 20),
            )

        # Transactions above the customer's alert threshold, with occasional bursts.
        for _ in range(_poisson(rng, TXN_RATE[customer.segment])):
            account = rng.choice(spend_accounts)
            at = local(_diurnal_minute(rng))
            emit(
                "cards",
                account,
                EventType.LARGE_TRANSACTION,
                at,
                amount=_amount(rng, 350, 1.1, 100),
            )
            if rng.random() < BURST_PROBABILITY:
                for _ in range(rng.randint(3, 7)):
                    at += timedelta(minutes=rng.uniform(1, 4))
                    emit(
                        "cards",
                        account,
                        EventType.LARGE_TRANSACTION,
                        at,
                        amount=_amount(rng, 180, 0.8, 100),
                    )
            if account is checking and rng.random() < TXN_TRIGGERS_LOW_BALANCE:
                emit(
                    "core",
                    checking,
                    EventType.LOW_BALANCE,
                    at + timedelta(minutes=rng.uniform(1, 30)),
                )

        for _ in range(_poisson(rng, LOW_BALANCE_RATE[customer.segment])):
            emit("core", checking, EventType.LOW_BALANCE, local(_diurnal_minute(rng)))

        for _ in range(_poisson(rng, INTERNATIONAL_RATE)):
            emit(
                "cards",
                rng.choice(spend_accounts),
                EventType.INTERNATIONAL_TRANSACTION,
                local(rng.uniform(0, 1440)),
                amount=_amount(rng, 150, 0.9, 5),
            )

        # Security: rare, any hour of the day or night.
        for _ in range(_poisson(rng, FRAUD_RATE)):
            account = rng.choice(spend_accounts)
            at = local(rng.uniform(0, 1440))
            emit("fraud", account, EventType.FRAUD_SUSPECTED, at, amount=_amount(rng, 400, 1.0, 20))
            if rng.random() < FRAUD_TRIGGERS_LOCK:
                emit(
                    "fraud",
                    account,
                    EventType.CARD_LOCKED,
                    at + timedelta(minutes=rng.uniform(1, 4)),
                )
        for _ in range(_poisson(rng, CARD_LOCK_RATE)):
            emit(
                "fraud",
                rng.choice(spend_accounts),
                EventType.CARD_LOCKED,
                local(_diurnal_minute(rng)),
            )
        for _ in range(_poisson(rng, NEW_DEVICE_RATE)):
            emit("auth", checking, EventType.NEW_DEVICE_LOGIN, local(rng.uniform(0, 1440)))

        for card in cards:
            if _poisson(rng, CREDIT_LIMIT_RATE_PER_CARD):
                emit("cards", card, EventType.CREDIT_LIMIT_CHANGE, local(_window_minute(rng, 1, 4)))

        if _poisson(rng, MARKETING_DRIP_RATE):
            emit(
                "mkt",
                checking,
                EventType.MARKETING_OFFER,
                local(_diurnal_minute(rng)),
                campaign_id="drip",
            )

    # Monthly cycles: statements for every account; due-soon and payment for cards.
    for account in accounts:
        for back in (1, 0):
            cycle = _statement_date(start, account.statement_day, months_back=back)

            def cycle_local(minute: float, offset: int = 0, c: date = cycle) -> datetime:
                return _at_local(c + timedelta(days=offset), minute, tz)

            emit("docs", account, EventType.STATEMENT_READY, cycle_local(_window_minute(rng, 1, 4)))
            if account.account_type not in CARD_ACCOUNT_TYPES:
                continue
            paid_on = rng.randint(5, 24) if rng.random() < ON_TIME_PAYMENT else None
            due_soon_day = 18
            if paid_on is None or paid_on > due_soon_day:
                minute = _window_minute(rng, 6, 7) if rng.random() < 0.5 else _diurnal_minute(rng)
                emit(
                    "billing",
                    account,
                    EventType.PAYMENT_DUE_SOON,
                    cycle_local(minute, due_soon_day),
                )
            if paid_on is not None:
                emit(
                    "billing",
                    account,
                    EventType.PAYMENT_RECEIVED,
                    cycle_local(_diurnal_minute(rng), paid_on),
                    amount=_amount(rng, 600, 0.8, 35),
                )


def _statement_date(start: date, statement_day: int, months_back: int) -> date:
    """The statement cut on/after `start`, or the one before it when months_back=1."""
    year, month = start.year, start.month
    if statement_day < start.day:
        month += 1
    month -= months_back
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return date(year, month, statement_day)


def _campaign_events(
    rng: random.Random,
    factory: _EventFactory,
    customers: list[SimCustomer],
    accounts: dict[int, list[SimAccount]],
    start: date,
) -> None:
    for campaign in CAMPAIGNS:
        launch = datetime.combine(
            start + timedelta(days=campaign.day), campaign.start_et, tzinfo=_EASTERN
        ).astimezone(UTC)
        for customer in customers:
            if rng.random() >= campaign.reach:
                continue
            checking = accounts[customer.id][0]
            at = launch + timedelta(minutes=rng.uniform(0, CAMPAIGN_SPREAD_MINUTES))
            factory.emit(
                "mkt", customer, checking, EventType.MARKETING_OFFER, at, campaign_id=campaign.id
            )


def _inject_retries(rng: random.Random, events: list[SimEvent]) -> list[SimEvent]:
    """Upstream retries: same source id, delivered again seconds to minutes later."""
    retries: list[SimEvent] = []
    for event in events:
        if rng.random() >= RETRY_PROBABILITY:
            continue
        copies = 2 if rng.random() < DOUBLE_RETRY_PROBABILITY else 1
        at = event.occurred_at
        for _ in range(copies):
            at += timedelta(seconds=rng.randint(5, 180))
            retries.append(replace(event, occurred_at=at, is_retry=True))
    return retries
