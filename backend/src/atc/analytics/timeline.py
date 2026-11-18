"""One customer's before/after view: every alert, explained in plain English."""

from datetime import datetime

from sqlmodel import Session, col, select

from atc.db.models import Account, AlertDecision, Digest, Event
from atc.directory.phones import service_phone
from atc.domain import AccountType, EventType
from atc.messages import preview
from atc.schemas import Timeline, TimelineItem, TimelineStep
from atc.simulator.models import SimAccount


def _accounts(session: Session, customer_id: int) -> dict[int, SimAccount]:
    return {
        a.id: SimAccount(
            id=a.id,
            customer_id=a.customer_id,
            account_type=AccountType(a.account_type),
            partner_code=a.partner_code,
            last4=a.last4,
            statement_day=a.statement_day,
        )
        for a in session.exec(select(Account).where(Account.customer_id == customer_id))
    }


def _items(session: Session, run_id: str, customer_id: int) -> list[TimelineItem]:
    accounts = _accounts(session, customer_id)
    rows = session.exec(
        select(AlertDecision, Event.account_id, Event.amount)
        .join(Event, col(Event.id) == col(AlertDecision.event_id))
        .where(AlertDecision.run_id == run_id, AlertDecision.customer_id == customer_id)
        .order_by(col(AlertDecision.requested_at))
    ).all()
    items: list[TimelineItem] = []
    for decision, account_id, amount in rows:
        account = accounts[account_id]
        phone = service_phone(account.account_type, account.partner_code)
        items.append(
            TimelineItem(
                kind="alert",
                alert_id=decision.alert_id,
                event_type=decision.event_type,
                priority=decision.priority,
                outcome=decision.outcome,
                rule=decision.decided_by_rule,
                explanation=decision.reason,
                steps=[TimelineStep(**s) for s in decision.trace],
                requested_at=decision.requested_at,
                delivered_at=decision.delivered_at,
                channels=decision.channels,
                preview=preview(EventType(decision.event_type), account, amount),
                account_last4=account.last4,
                service_phone=phone.phone,
            )
        )
    for digest in session.exec(
        select(Digest).where(Digest.run_id == run_id, Digest.customer_id == customer_id)
    ):
        n = digest.alert_count
        items.append(
            TimelineItem(
                kind="digest",
                alert_id=None,
                event_type=None,
                priority="low",
                outcome="SENT",
                rule="digest",
                explanation=f"One daily summary replaced {n} separate alert{'s' * (n != 1)}.",
                steps=[],
                requested_at=None,
                delivered_at=digest.delivered_at,
                channels=[digest.channel],
                preview=f"Your Northgate daily digest: {n} account update{'s' * (n != 1)}.",
                account_last4=None,
                service_phone=None,
                digest_count=n,
            )
        )
    items.sort(key=_when)
    return items


def _when(item: TimelineItem) -> datetime:
    """Delivered items sort by delivery time; suppressed ones by when they were requested."""
    when = item.delivered_at or item.requested_at
    assert when is not None
    return when


def customer_timeline(
    session: Session, customer_id: int, run_id: str, baseline_run_id: str
) -> Timeline:
    return Timeline(
        customer_id=customer_id,
        run_id=run_id,
        baseline=_items(session, baseline_run_id, customer_id),
        atc=_items(session, run_id, customer_id),
    )
