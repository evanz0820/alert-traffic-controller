"""Synthetic customers and accounts."""

import random

from faker import Faker

from atc.directory.phones import COBRAND_PARTNERS
from atc.domain import AccountType, Engagement, Segment
from atc.simulator.models import SimAccount, SimCustomer

# Rough share of US population per zone. Phoenix (no DST) and Honolulu keep the
# quiet-hours logic honest across zones that don't shift clocks.
TIMEZONE_WEIGHTS: dict[str, float] = {
    "America/New_York": 0.46,
    "America/Chicago": 0.28,
    "America/Denver": 0.07,
    "America/Phoenix": 0.03,
    "America/Los_Angeles": 0.13,
    "America/Anchorage": 0.015,
    "Pacific/Honolulu": 0.015,
}

SEGMENT_WEIGHTS: dict[Segment, float] = {
    Segment.MASS: 0.60,
    Segment.MASS_AFFLUENT: 0.25,
    Segment.SENIOR: 0.15,
}

ENGAGEMENT_BY_SEGMENT: dict[Segment, dict[Engagement, float]] = {
    Segment.MASS: {Engagement.HIGH: 0.35, Engagement.MEDIUM: 0.40, Engagement.LOW: 0.25},
    Segment.MASS_AFFLUENT: {Engagement.HIGH: 0.50, Engagement.MEDIUM: 0.35, Engagement.LOW: 0.15},
    Segment.SENIOR: {Engagement.HIGH: 0.15, Engagement.MEDIUM: 0.35, Engagement.LOW: 0.50},
}

# Probability each channel is turned OFF.
OPT_OUT = {"push": 0.15, "email": 0.10, "sms": 0.35}
SENIOR_PUSH_OPT_OUT = 0.40


def _pick[T](rng: random.Random, weights: dict[T, float]) -> T:
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]


def generate_customers(rng: random.Random, faker: Faker, count: int) -> list[SimCustomer]:
    customers: list[SimCustomer] = []
    for cid in range(1, count + 1):
        segment = _pick(rng, SEGMENT_WEIGHTS)
        push_off = SENIOR_PUSH_OPT_OUT if segment is Segment.SENIOR else OPT_OUT["push"]
        push = rng.random() >= push_off
        email = rng.random() >= OPT_OUT["email"]
        sms = rng.random() >= OPT_OUT["sms"]
        if not (push or email):
            # Everyone keeps at least one digital channel; SMS-only is unrealistic here.
            email = True
        customers.append(
            SimCustomer(
                id=cid,
                name=faker.name(),
                timezone=_pick(rng, TIMEZONE_WEIGHTS),
                segment=segment,
                engagement=_pick(rng, ENGAGEMENT_BY_SEGMENT[segment]),
                push_enabled=push,
                email_enabled=email,
                sms_enabled=sms,
            )
        )
    return customers


def generate_accounts(rng: random.Random, customers: list[SimCustomer]) -> list[SimAccount]:
    """Every customer has checking, plus 0-2 of savings / Northgate card / cobrand card."""
    accounts: list[SimAccount] = []
    next_id = 1

    def add(customer_id: int, account_type: AccountType, partner: str | None = None) -> None:
        nonlocal next_id
        accounts.append(
            SimAccount(
                id=next_id,
                customer_id=customer_id,
                account_type=account_type,
                partner_code=partner,
                last4=f"{rng.randrange(10_000):04d}",
                statement_day=rng.randint(1, 28),
            )
        )
        next_id += 1

    for c in customers:
        add(c.id, AccountType.CHECKING)
        extras = rng.choices([0, 1, 2], weights=[0.30, 0.45, 0.25], k=1)[0]
        pool = [AccountType.SAVINGS, AccountType.NORTHGATE_CARD, AccountType.COBRAND_CARD]
        for account_type in rng.sample(pool, k=extras):
            partner = (
                _pick_partner(rng, c.segment) if account_type is AccountType.COBRAND_CARD else None
            )
            add(c.id, account_type, partner)
    return accounts


def _pick_partner(rng: random.Random, segment: Segment) -> str:
    codes = [p.code for p in COBRAND_PARTNERS]
    weights = [0.80, 0.10, 0.10] if segment is Segment.SENIOR else [0.20, 0.45, 0.35]
    return rng.choices(codes, weights=weights, k=1)[0]
