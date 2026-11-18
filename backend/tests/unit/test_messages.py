import pytest

from atc.directory.phones import service_phone
from atc.domain import AccountType, EventType
from atc.messages import preview
from atc.simulator.models import SimAccount

ACCOUNTS = [
    SimAccount(1, 1, AccountType.CHECKING, None, "1111", 5),
    SimAccount(2, 1, AccountType.NORTHGATE_CARD, None, "2222", 5),
    SimAccount(3, 1, AccountType.COBRAND_CARD, "AARP", "3333", 5),
    SimAccount(4, 1, AccountType.COBRAND_CARD, "SUMMIT", "4444", 5),
    SimAccount(5, 1, AccountType.COBRAND_CARD, "HARVEST", "5555", 5),
]
WITH_PHONE = [
    EventType.FRAUD_SUSPECTED,
    EventType.CARD_LOCKED,
    EventType.NEW_DEVICE_LOGIN,
    EventType.LARGE_TRANSACTION,
    EventType.LOW_BALANCE,
]


@pytest.mark.parametrize("event_type", WITH_PHONE)
@pytest.mark.parametrize("account", ACCOUNTS, ids=lambda a: a.partner_code or a.account_type)
def test_alert_text_carries_the_right_service_line(
    event_type: EventType, account: SimAccount
) -> None:
    text = preview(event_type, account, 120.0)
    expected = service_phone(account.account_type, account.partner_code).phone
    assert expected in text
    if account.account_type is AccountType.COBRAND_CARD:
        assert "1-800-555-0100" not in text
        assert "1-800-555-0110" not in text


@pytest.mark.parametrize("event_type", list(EventType))
def test_every_event_type_has_copy(event_type: EventType) -> None:
    text = preview(event_type, ACCOUNTS[0], None)
    assert text and "None" not in text
