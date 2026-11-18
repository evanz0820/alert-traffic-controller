"""Rule 5: hold non-critical alerts during the customer's local quiet hours."""

from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.domain import Priority
from atc.engine.timeutil import format_clock, format_local, in_window, next_local_time
from atc.engine.types import Action, AlertRequest, CustomerContext, Decision


class QuietHours:
    name: ClassVar[RuleName] = RuleName.QUIET_HOURS

    def applies_to(self, req: AlertRequest) -> bool:
        return req.priority is not Priority.CRITICAL

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        cfg = config.rules.quiet_hours
        tz = ctx.profile.tz
        local = decision.scheduled_at.astimezone(tz)
        if not in_window(local.time().replace(tzinfo=None), cfg.start, cfg.end):
            return decision

        window = f"{format_clock(cfg.start)}-{format_clock(cfg.end)}"
        if req.priority is Priority.MARKETING:
            return decision.suppress(
                self.name, f"Marketing is never sent during quiet hours ({window} local)."
            )
        if (
            req.priority is Priority.HIGH
            and req.amount is not None
            and req.amount >= cfg.high_amount_exemption
        ):
            return decision.note(
                self.name,
                Action.PASS,
                f"Sent during quiet hours: ${req.amount:,.2f} is above the "
                f"${cfg.high_amount_exemption:,.0f} urgency threshold.",
            )
        until = next_local_time(decision.scheduled_at, tz, cfg.end)
        return decision.delay(
            self.name,
            f"Held until {format_local(until, tz)}: arrived at {format_local(local, tz)}, "
            f"during quiet hours.",
            until,
        )
