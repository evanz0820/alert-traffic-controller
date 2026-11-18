"""Rule 1: critical alerts skip every other rule and go out immediately on all channels."""

from dataclasses import replace
from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.domain import Channel, Outcome, Priority
from atc.engine.types import Action, AlertRequest, CustomerContext, Decision

# SMS leads because it is the channel most likely to be seen within seconds.
CRITICAL_CHANNEL_ORDER: tuple[Channel, ...] = (Channel.SMS, Channel.PUSH, Channel.EMAIL)


def critical_channels(enabled: frozenset[Channel]) -> tuple[Channel, ...]:
    """Every enabled channel, plus SMS always (security alerts override SMS opt-out)."""
    wanted = enabled | {Channel.SMS}
    return tuple(c for c in CRITICAL_CHANNEL_ORDER if c in wanted)


class CriticalBypass:
    name: ClassVar[RuleName] = RuleName.CRITICAL_BYPASS

    def applies_to(self, req: AlertRequest) -> bool:
        return req.priority is Priority.CRITICAL

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        channels = critical_channels(ctx.profile.enabled_channels)
        names = ", ".join(c.value.upper() if c is Channel.SMS else c.value for c in channels)
        reason = f"Critical security alert: sent instantly on {names}. No rule can hold it."
        return replace(
            decision.note(self.name, Action.SEND, reason),
            outcome=Outcome.SENT,
            decided_by=self.name,
            reason=reason,
            channel=channels[0],
            channels=channels,
            scheduled_at=req.requested_at,
            terminal=True,
        )
