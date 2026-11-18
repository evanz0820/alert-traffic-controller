"""Rule 2: suppress upstream retries that reuse an already-seen source id."""

from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.domain import Priority
from atc.engine.types import AlertRequest, CustomerContext, Decision


class Dedup:
    name: ClassVar[RuleName] = RuleName.DEDUP

    def applies_to(self, req: AlertRequest) -> bool:
        return req.priority is not Priority.CRITICAL

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        first = ctx.seen_sources.get(req.source_id)
        if first is None or first == req.alert_id:
            return decision
        return decision.suppress(
            self.name, f"Duplicate of alert {first}: upstream retried event {req.source_id}."
        )
