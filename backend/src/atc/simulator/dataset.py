"""Build the full synthetic dataset deterministically from a seed."""

import random
from datetime import date

from faker import Faker

from atc.simulator.customers import generate_accounts, generate_customers
from atc.simulator.events import generate_events
from atc.simulator.models import Dataset

DEFAULT_SEED = 42
DEFAULT_CUSTOMERS = 500
# 30 days that straddle the US fall-back DST change (Nov 1, 2026).
DEFAULT_START = date(2026, 10, 19)
DEFAULT_DAYS = 30


def build_dataset(
    seed: int = DEFAULT_SEED,
    customers: int = DEFAULT_CUSTOMERS,
    start: date = DEFAULT_START,
    days: int = DEFAULT_DAYS,
) -> Dataset:
    rng = random.Random(seed)
    faker = Faker("en_US")
    faker.seed_instance(seed)

    people = generate_customers(rng, faker, customers)
    accounts = generate_accounts(rng, people)
    events = generate_events(rng, people, accounts, start, days)
    return Dataset(
        seed=seed,
        start=start,
        days=days,
        customers=tuple(people),
        accounts=tuple(accounts),
        events=tuple(events),
    )
