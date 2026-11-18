"""Persistence helpers. All datetimes are stored and returned as tz-aware UTC."""

from datetime import UTC, datetime

from sqlalchemy import Engine, insert
from sqlmodel import Session, SQLModel, select

from atc.db.models import Account, Customer, Event, ServicePhone
from atc.directory.phones import SERVICE_PHONES
from atc.domain import AccountType, Engagement, EventType, Segment
from atc.simulator.models import Dataset, SimAccount, SimCustomer, SimEvent


def to_db_time(value: datetime) -> datetime:
    return value.astimezone(UTC)


def from_db_time(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def reset_schema(engine: Engine) -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def write_dataset(session: Session, ds: Dataset) -> None:
    session.connection().execute(
        insert(ServicePhone),
        [
            {
                "account_type": p.account_type.value,
                "partner_code": p.partner_code,
                "phone": p.phone,
                "label": p.label,
            }
            for p in SERVICE_PHONES
        ],
    )
    session.connection().execute(
        insert(Customer),
        [
            {
                "id": c.id,
                "name": c.name,
                "timezone": c.timezone,
                "segment": c.segment.value,
                "engagement": c.engagement.value,
                "push_enabled": c.push_enabled,
                "email_enabled": c.email_enabled,
                "sms_enabled": c.sms_enabled,
            }
            for c in ds.customers
        ],
    )
    session.connection().execute(
        insert(Account),
        [
            {
                "id": a.id,
                "customer_id": a.customer_id,
                "account_type": a.account_type.value,
                "partner_code": a.partner_code,
                "last4": a.last4,
                "statement_day": a.statement_day,
            }
            for a in ds.accounts
        ],
    )
    session.connection().execute(
        insert(Event),
        [
            {
                "id": i,
                "source_id": e.source_id,
                "customer_id": e.customer_id,
                "account_id": e.account_id,
                "event_type": e.event_type.value,
                "occurred_at": to_db_time(e.occurred_at),
                "amount": e.amount,
                "campaign_id": e.campaign_id,
                "is_retry": e.is_retry,
            }
            for i, e in enumerate(ds.events, start=1)
        ],
    )
    session.commit()


def load_customers(session: Session) -> list[SimCustomer]:
    return [
        SimCustomer(
            id=c.id,
            name=c.name,
            timezone=c.timezone,
            segment=Segment(c.segment),
            engagement=Engagement(c.engagement),
            push_enabled=c.push_enabled,
            email_enabled=c.email_enabled,
            sms_enabled=c.sms_enabled,
        )
        for c in session.exec(select(Customer).order_by(Customer.id))  # type: ignore[arg-type]
    ]


def load_accounts(session: Session) -> list[SimAccount]:
    return [
        SimAccount(
            id=a.id,
            customer_id=a.customer_id,
            account_type=AccountType(a.account_type),
            partner_code=a.partner_code,
            last4=a.last4,
            statement_day=a.statement_day,
        )
        for a in session.exec(select(Account).order_by(Account.id))  # type: ignore[arg-type]
    ]


def load_events(session: Session) -> list[tuple[int, SimEvent]]:
    """Events in stream order, paired with their database id."""
    return [
        (
            e.id,
            SimEvent(
                source_id=e.source_id,
                customer_id=e.customer_id,
                account_id=e.account_id,
                event_type=EventType(e.event_type),
                occurred_at=from_db_time(e.occurred_at),
                amount=e.amount,
                campaign_id=e.campaign_id,
                is_retry=e.is_retry,
            ),
        )
        for e in session.exec(select(Event).order_by(Event.id))  # type: ignore[arg-type]
    ]
