"""Customer-facing alert copy, including the correct service phone for the account."""

from atc.directory.phones import service_phone
from atc.domain import AccountType, EventType
from atc.simulator.models import SimAccount

_ACCOUNT_LABEL = {
    AccountType.CHECKING: "checking",
    AccountType.SAVINGS: "savings",
    AccountType.NORTHGATE_CARD: "Northgate card",
    AccountType.COBRAND_CARD: "card",
}


def _money(amount: float | None) -> str:
    return f"${amount:,.2f}" if amount is not None else "a transaction"


def preview(event_type: EventType, account: SimAccount, amount: float | None) -> str:
    phone = service_phone(account.account_type, account.partner_code).phone
    acct = f"{_ACCOUNT_LABEL[account.account_type]} ending {account.last4}"
    match event_type:
        case EventType.FRAUD_SUSPECTED:
            return (
                f"Did you attempt {_money(amount)} on your {acct}? Reply YES or NO. "
                f"If not you, call {phone} now."
            )
        case EventType.CARD_LOCKED:
            return f"We locked your {acct} to protect you. Call {phone} to unlock it."
        case EventType.NEW_DEVICE_LOGIN:
            return f"New device signed in to your account. Not you? Call {phone} immediately."
        case EventType.LOW_BALANCE:
            return f"Your {acct} balance is below your alert threshold. Questions? {phone}"
        case EventType.LARGE_TRANSACTION:
            return f"{_money(amount)} charged to your {acct}. Not you? Call {phone}."
        case EventType.INTERNATIONAL_TRANSACTION:
            return f"International purchase of {_money(amount)} on your {acct}. Call {phone}."
        case EventType.PAYMENT_DUE_SOON:
            return f"Your {acct} payment is due in 3 days. Questions? {phone}"
        case EventType.DEPOSIT:
            return f"Deposit of {_money(amount)} posted to your {acct}."
        case EventType.PAYMENT_RECEIVED:
            return f"We received your {_money(amount)} payment on your {acct}. Thank you."
        case EventType.STATEMENT_READY:
            return f"Your {acct} statement is ready to view."
        case EventType.CREDIT_LIMIT_CHANGE:
            return f"Your credit limit on {acct} has changed. Questions? {phone}"
        case EventType.MARKETING_OFFER:
            return "Exclusive offer: earn 5% cash back this week. Tap to activate."
