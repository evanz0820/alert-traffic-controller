"""Rule 3: never use a channel the customer turned off; reroute to the next allowed one."""

from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.domain import Priority
from atc.engine.types import AlertRequest, CustomerContext, Decision


class PreferenceFilter:
    name: ClassVar[RuleName] = RuleName.PREFERENCE_FILTER

    def applies_to(self, req: AlertRequest) -> bool:
        return req.priority is not Priority.CRITICAL

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        enabled = ctx.profile.enabled_channels
        if decision.channel in enabled:
            return decision
        order = config.rules.preference_filter.fallback_order
        fallback = next((c for c in order if c in enabled), None)
        if fallback is None:
            return decision.suppress(self.name, "Customer has opted out of every channel.")
        current = decision.channel.value if decision.channel else "that channel"
        return decision.reroute(
            self.name,
            f"Customer turned off {current} alerts, so this went by {fallback.value} instead.",
            fallback,
        )
