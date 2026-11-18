"""Rule 8: pick the channel by engagement and fall back to email when push goes unread."""

from dataclasses import replace
from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.domain import Channel, Engagement, Outcome, Priority
from atc.engine.timeutil import stable_unit
from atc.engine.types import Action, AlertRequest, CustomerContext, Decision

CHANNEL_ORDER: dict[Engagement, tuple[Channel, ...]] = {
    Engagement.HIGH: (Channel.PUSH, Channel.EMAIL, Channel.SMS),
    Engagement.MEDIUM: (Channel.PUSH, Channel.EMAIL, Channel.SMS),
    Engagement.LOW: (Channel.EMAIL, Channel.PUSH, Channel.SMS),
}


def push_opened(alert_id: str, probability: float) -> bool:
    """Simulated open within the window: deterministic per alert, so runs are repeatable."""
    return stable_unit(alert_id, "push-open") < probability


class ChannelRouting:
    name: ClassVar[RuleName] = RuleName.CHANNEL_ROUTING

    def applies_to(self, req: AlertRequest) -> bool:
        return req.priority is not Priority.CRITICAL

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        cfg = config.rules.channel_routing
        profile = ctx.profile
        enabled = profile.enabled_channels
        chosen = next((c for c in CHANNEL_ORDER[profile.engagement] if c in enabled), None)
        if chosen is None:
            return decision
        if chosen is not decision.channel:
            decision = decision.reroute(
                self.name,
                f"Sent by {chosen.value}: {chosen.value} works best for customers with "
                f"{profile.engagement.value} app engagement.",
                chosen,
            )

        if chosen is not Channel.PUSH or Channel.EMAIL not in enabled:
            return replace(decision, channels=(chosen,))
        if push_opened(req.alert_id, cfg.open_probability[profile.engagement]):
            return replace(decision, channels=(Channel.PUSH,))

        window = cfg.push_open_window_minutes
        reason = f"Push wasn't opened within {window} min, so it followed up by email."
        decision = decision.note(self.name, Action.FALLBACK, reason)
        if decision.outcome is Outcome.DELAYED:
            return replace(decision, channels=(Channel.PUSH, Channel.EMAIL))
        return replace(
            decision,
            channels=(Channel.PUSH, Channel.EMAIL),
            channel=Channel.EMAIL,
            outcome=Outcome.REROUTED,
            decided_by=self.name,
            reason=reason,
        )
