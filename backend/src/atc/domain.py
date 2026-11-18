"""Core domain vocabulary shared by the simulator, engine, API, and dashboard."""

from enum import StrEnum


class EventType(StrEnum):
    DEPOSIT = "deposit"
    LOW_BALANCE = "low_balance"
    LARGE_TRANSACTION = "large_transaction"
    INTERNATIONAL_TRANSACTION = "international_transaction"
    FRAUD_SUSPECTED = "fraud_suspected"
    CARD_LOCKED = "card_locked"
    NEW_DEVICE_LOGIN = "new_device_login"
    PAYMENT_DUE_SOON = "payment_due_soon"
    PAYMENT_RECEIVED = "payment_received"
    STATEMENT_READY = "statement_ready"
    CREDIT_LIMIT_CHANGE = "credit_limit_change"
    MARKETING_OFFER = "marketing_offer"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    LOW = "low"
    MARKETING = "marketing"

    @property
    def rank(self) -> int:
        """Higher rank = more important. Used when deciding what to drop first."""
        return _PRIORITY_RANK[self]


_PRIORITY_RANK: dict[Priority, int] = {
    Priority.CRITICAL: 3,
    Priority.HIGH: 2,
    Priority.LOW: 1,
    Priority.MARKETING: 0,
}


class Channel(StrEnum):
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"


class Outcome(StrEnum):
    SENT = "SENT"
    SUPPRESSED = "SUPPRESSED"
    DELAYED = "DELAYED"
    BATCHED_TO_DIGEST = "BATCHED_TO_DIGEST"
    REROUTED = "REROUTED"


class Segment(StrEnum):
    MASS = "mass"
    MASS_AFFLUENT = "mass_affluent"
    SENIOR = "senior"


class Engagement(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    NORTHGATE_CARD = "northgate_card"
    COBRAND_CARD = "cobrand_card"


CARD_ACCOUNT_TYPES: frozenset[AccountType] = frozenset(
    {AccountType.NORTHGATE_CARD, AccountType.COBRAND_CARD}
)

PRIORITY_BY_EVENT: dict[EventType, Priority] = {
    EventType.FRAUD_SUSPECTED: Priority.CRITICAL,
    EventType.CARD_LOCKED: Priority.CRITICAL,
    EventType.NEW_DEVICE_LOGIN: Priority.CRITICAL,
    EventType.LOW_BALANCE: Priority.HIGH,
    EventType.LARGE_TRANSACTION: Priority.HIGH,
    EventType.INTERNATIONAL_TRANSACTION: Priority.HIGH,
    EventType.PAYMENT_DUE_SOON: Priority.HIGH,
    EventType.DEPOSIT: Priority.LOW,
    EventType.PAYMENT_RECEIVED: Priority.LOW,
    EventType.STATEMENT_READY: Priority.LOW,
    EventType.CREDIT_LIMIT_CHANGE: Priority.LOW,
    EventType.MARKETING_OFFER: Priority.MARKETING,
}

# The channel each upstream producer asks for today, before ATC gets involved.
REQUESTED_CHANNEL_BY_EVENT: dict[EventType, Channel] = {
    EventType.FRAUD_SUSPECTED: Channel.SMS,
    EventType.CARD_LOCKED: Channel.SMS,
    EventType.NEW_DEVICE_LOGIN: Channel.PUSH,
    EventType.LOW_BALANCE: Channel.PUSH,
    EventType.LARGE_TRANSACTION: Channel.PUSH,
    EventType.INTERNATIONAL_TRANSACTION: Channel.PUSH,
    EventType.PAYMENT_DUE_SOON: Channel.EMAIL,
    EventType.DEPOSIT: Channel.PUSH,
    EventType.PAYMENT_RECEIVED: Channel.EMAIL,
    EventType.STATEMENT_READY: Channel.EMAIL,
    EventType.CREDIT_LIMIT_CHANGE: Channel.EMAIL,
    EventType.MARKETING_OFFER: Channel.EMAIL,
}


def priority_of(event_type: EventType) -> Priority:
    return PRIORITY_BY_EVENT[event_type]
