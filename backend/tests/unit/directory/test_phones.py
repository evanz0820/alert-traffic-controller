import pytest

from atc.directory.phones import (
    COBRAND_PARTNERS,
    SERVICE_PHONES,
    UnknownPartnerError,
    service_phone,
)
from atc.domain import AccountType
from atc.simulator.models import Dataset

BANK_LINE = "1-800-555-0100"
CARD_LINE = "1-800-555-0110"


@pytest.mark.parametrize(
    ("account_type", "expected"),
    [
        (AccountType.CHECKING, BANK_LINE),
        (AccountType.SAVINGS, BANK_LINE),
        (AccountType.NORTHGATE_CARD, CARD_LINE),
    ],
)
def test_bank_accounts_use_northgate_lines(account_type: AccountType, expected: str) -> None:
    assert service_phone(account_type).phone == expected


@pytest.mark.parametrize(
    ("partner", "expected"),
    [("AARP", "1-800-555-0120"), ("SUMMIT", "1-800-555-0130"), ("HARVEST", "1-800-555-0140")],
)
def test_cobrand_cards_use_partner_line(partner: str, expected: str) -> None:
    phone = service_phone(AccountType.COBRAND_CARD, partner)
    assert phone.phone == expected
    assert phone.partner_code == partner


def test_cobrand_never_falls_back_to_a_bank_line() -> None:
    bank_numbers = {BANK_LINE, CARD_LINE}
    for partner in COBRAND_PARTNERS:
        assert service_phone(AccountType.COBRAND_CARD, partner.code).phone not in bank_numbers


def test_every_partner_has_a_distinct_line() -> None:
    numbers = [service_phone(AccountType.COBRAND_CARD, p.code).phone for p in COBRAND_PARTNERS]
    assert len(set(numbers)) == len(COBRAND_PARTNERS)


def test_partner_code_is_normalised() -> None:
    assert service_phone(AccountType.COBRAND_CARD, " aarp ").partner_code == "AARP"


def test_partner_code_is_ignored_for_bank_accounts() -> None:
    assert service_phone(AccountType.CHECKING, "AARP").phone == BANK_LINE


@pytest.mark.parametrize("partner", [None, "", "   "])
def test_cobrand_without_partner_raises(partner: str | None) -> None:
    with pytest.raises(UnknownPartnerError, match="missing a partner"):
        service_phone(AccountType.COBRAND_CARD, partner)


def test_unknown_partner_raises() -> None:
    with pytest.raises(UnknownPartnerError, match="ACME"):
        service_phone(AccountType.COBRAND_CARD, "acme")


def test_all_numbers_are_fictional_555_01xx() -> None:
    for entry in SERVICE_PHONES:
        assert entry.phone.startswith("1-800-555-01")


def test_every_simulated_account_resolves_a_phone(dataset: Dataset) -> None:
    for account in dataset.accounts:
        phone = service_phone(account.account_type, account.partner_code)
        if account.account_type is AccountType.COBRAND_CARD:
            assert phone.partner_code == account.partner_code
