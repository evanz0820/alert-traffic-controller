"""Customer service phone directory.

Every alert tells the customer whom to call. Bank-branded accounts route to Northgate
service lines; cobrand cards must route to the partner's dedicated line. This mirrors
real core-banking logic where the number is chosen by account type and cobrand partner.

All numbers use the fictional 555-01xx range.
"""

from dataclasses import dataclass

from atc.domain import AccountType


class UnknownPartnerError(ValueError):
    """Raised when a cobrand account references a partner with no configured line."""


@dataclass(frozen=True, slots=True)
class CobrandPartner:
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class ServicePhone:
    account_type: AccountType
    partner_code: str  # "" for bank-branded accounts
    phone: str
    label: str


COBRAND_PARTNERS: tuple[CobrandPartner, ...] = (
    CobrandPartner("AARP", "AARP Rewards"),
    CobrandPartner("SUMMIT", "Summit Air Miles"),
    CobrandPartner("HARVEST", "Harvest Market Rewards"),
)

SERVICE_PHONES: tuple[ServicePhone, ...] = (
    ServicePhone(AccountType.CHECKING, "", "1-800-555-0100", "Northgate Customer Care"),
    ServicePhone(AccountType.SAVINGS, "", "1-800-555-0100", "Northgate Customer Care"),
    ServicePhone(AccountType.NORTHGATE_CARD, "", "1-800-555-0110", "Northgate Card Services"),
    ServicePhone(AccountType.COBRAND_CARD, "AARP", "1-800-555-0120", "AARP Rewards Card Services"),
    ServicePhone(
        AccountType.COBRAND_CARD, "SUMMIT", "1-800-555-0130", "Summit Air Miles Card Services"
    ),
    ServicePhone(
        AccountType.COBRAND_CARD, "HARVEST", "1-800-555-0140", "Harvest Market Card Services"
    ),
)

_INDEX: dict[tuple[AccountType, str], ServicePhone] = {
    (p.account_type, p.partner_code): p for p in SERVICE_PHONES
}


def service_phone(account_type: AccountType, partner_code: str | None = None) -> ServicePhone:
    """Return the service line for an account.

    Cobrand cards require a known partner code and never fall back to the bank line,
    because sending a partner's customer to the wrong desk is a real service failure.
    Partner codes are ignored for bank-branded accounts.
    """
    if account_type is AccountType.COBRAND_CARD:
        code = (partner_code or "").strip().upper()
        if not code:
            raise UnknownPartnerError("cobrand account is missing a partner code")
        try:
            return _INDEX[(account_type, code)]
        except KeyError:
            raise UnknownPartnerError(f"no service line configured for partner {code!r}") from None
    return _INDEX[(account_type, "")]
