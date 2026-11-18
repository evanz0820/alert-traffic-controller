"""Pipeline rules. Each module exposes one class implementing `atc.engine.types.Rule`."""

from atc.config import RuleName
from atc.engine.rules.critical_bypass import CriticalBypass
from atc.engine.rules.dedup import Dedup
from atc.engine.rules.digest import Digest
from atc.engine.rules.fatigue_gate import FatigueGate
from atc.engine.rules.frequency_cap import FrequencyCap
from atc.engine.rules.preference import PreferenceFilter
from atc.engine.rules.quiet_hours import QuietHours
from atc.engine.rules.routing import ChannelRouting
from atc.engine.types import Rule

RULES: dict[RuleName, Rule] = {
    rule.name: rule
    for rule in (
        CriticalBypass(),
        Dedup(),
        PreferenceFilter(),
        FatigueGate(),
        QuietHours(),
        FrequencyCap(),
        Digest(),
        ChannelRouting(),
    )
}

__all__ = ["RULES"]
