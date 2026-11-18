from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import ColumnElement
from sqlmodel import col, or_, select

from atc.analytics.timeline import customer_timeline
from atc.api.deps import SessionDep, get_atc_run
from atc.db.models import Account, Customer, CustomerRunStat
from atc.directory.phones import service_phone
from atc.domain import AccountType
from atc.schemas import AccountInfo, CustomerDetail, CustomerListItem, Pair, Timeline

router = APIRouter(prefix="/customers", tags=["customers"])


def _stats(session: SessionDep, run_id: str) -> dict[int, CustomerRunStat]:
    rows = session.exec(select(CustomerRunStat).where(CustomerRunStat.run_id == run_id))
    return {s.customer_id: s for s in rows}


@router.get("", response_model=list[CustomerListItem])
def list_customers(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=80)] = None,
    run: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
) -> list[CustomerListItem]:
    stmt = select(Customer).order_by(col(Customer.id))
    if q:
        term = q.strip()
        clauses: list[ColumnElement[bool]] = [col(Customer.name).ilike(f"%{term}%")]
        if term.isdigit():
            clauses.append(col(Customer.id) == int(term))
        stmt = stmt.where(or_(*clauses))
    customers = session.exec(stmt.limit(limit)).all()

    atc_run = get_atc_run(session, run)
    assert atc_run.baseline_run_id is not None
    atc, base = _stats(session, atc_run.id), _stats(session, atc_run.baseline_run_id)
    return [
        CustomerListItem(
            id=c.id,
            name=c.name,
            segment=c.segment,
            engagement=c.engagement,
            timezone=c.timezone,
            fatigue_baseline=base[c.id].fatigue_score_mean if c.id in base else None,
            fatigue_atc=atc[c.id].fatigue_score_mean if c.id in atc else None,
        )
        for c in customers
    ]


@router.get("/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: int, session: SessionDep, run: str | None = None) -> CustomerDetail:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(404, f"customer {customer_id} not found")
    atc_run = get_atc_run(session, run)
    assert atc_run.baseline_run_id is not None
    atc = session.get(CustomerRunStat, (atc_run.id, customer_id))
    base = session.get(CustomerRunStat, (atc_run.baseline_run_id, customer_id))
    if atc is None or base is None:
        raise HTTPException(404, "no stats for this customer in the selected run")

    accounts = []
    for a in session.exec(
        select(Account).where(Account.customer_id == customer_id).order_by(col(Account.id))
    ):
        phone = service_phone(AccountType(a.account_type), a.partner_code)
        accounts.append(
            AccountInfo(
                id=a.id,
                account_type=a.account_type,
                partner_code=a.partner_code,
                last4=a.last4,
                service_phone=phone.phone,
                service_label=phone.label,
            )
        )
    return CustomerDetail(
        **customer.model_dump(),
        accounts=accounts,
        fatigue=Pair(baseline=base.fatigue_score_mean, atc=atc.fatigue_score_mean),
        fatigue_peak=Pair(baseline=base.fatigue_score_peak, atc=atc.fatigue_score_peak),
        alerts_delivered=Pair(baseline=base.alerts_delivered, atc=atc.alerts_delivered),
        marketing_paused=atc.marketing_paused,
    )


@router.get("/{customer_id}/timeline", response_model=Timeline)
def get_timeline(customer_id: int, session: SessionDep, run: str | None = None) -> Timeline:
    if session.get(Customer, customer_id) is None:
        raise HTTPException(404, f"customer {customer_id} not found")
    atc_run = get_atc_run(session, run)
    assert atc_run.baseline_run_id is not None
    return customer_timeline(session, customer_id, atc_run.id, atc_run.baseline_run_id)
