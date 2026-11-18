"""Rule 7: bundle low-priority alerts into one daily digest per customer."""

from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.engine.timeutil import format_clock, next_local_time
from atc.engine.types import AlertRequest, CustomerContext, Decision


class Digest:
    name: ClassVar[RuleName] = RuleName.DIGEST

    def applies_to(self, req: AlertRequest) -> bool:
        # Eligibility is config-driven, so it is checked in apply().
        return True

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        cfg = config.rules.digest
        if req.event_type not in cfg.event_types:
            return decision
        deliver_at = next_local_time(decision.scheduled_at, ctx.profile.tz, cfg.send_at)
        return decision.batch(
            self.name,
            f"Bundled into the {format_clock(cfg.send_at)} daily digest instead of a "
            f"separate alert.",
            deliver_at,
        )
