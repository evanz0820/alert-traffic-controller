"""Rule 4: pause marketing for customers whose fatigue score is above the threshold."""

from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.domain import Priority
from atc.engine.types import AlertRequest, CustomerContext, Decision


class FatigueGate:
    name: ClassVar[RuleName] = RuleName.FATIGUE_GATE

    def applies_to(self, req: AlertRequest) -> bool:
        return req.priority is Priority.MARKETING

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        threshold = config.rules.fatigue_gate.threshold
        if ctx.fatigue_score <= threshold:
            return decision
        return decision.suppress(
            self.name,
            f"Marketing paused: fatigue score {ctx.fatigue_score:.0f}/100 is above the "
            f"{threshold:.0f} limit.",
        )
