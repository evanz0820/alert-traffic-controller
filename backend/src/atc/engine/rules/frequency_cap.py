"""Rule 6: cap non-critical alerts per day and hour; lowest priority goes first.

High-priority alerts count toward the budget but are never capped themselves. Low alerts
over the cap fall into the digest; marketing over the cap is dropped.
"""

from datetime import timedelta
from typing import ClassVar

from atc.config import RuleName, RulesConfig
from atc.domain import Priority
from atc.engine.timeutil import format_clock, next_local_time
from atc.engine.types import AlertRequest, CustomerContext, Decision


class FrequencyCap:
    name: ClassVar[RuleName] = RuleName.FREQUENCY_CAP

    def applies_to(self, req: AlertRequest) -> bool:
        return req.priority in (Priority.LOW, Priority.MARKETING)

    def apply(
        self, req: AlertRequest, decision: Decision, ctx: CustomerContext, config: RulesConfig
    ) -> Decision:
        cfg = config.rules.frequency_cap
        tz = ctx.profile.tz
        at = decision.scheduled_at
        local_day = at.astimezone(tz).date()
        hour_start = at - timedelta(hours=1)
        week_start = at - timedelta(days=7)

        day = hour = mkt_day = mkt_week = 0
        for d in ctx.deliveries:
            if d.priority is Priority.CRITICAL:
                continue
            same_day = d.at.astimezone(tz).date() == local_day
            day += same_day
            hour += hour_start < d.at <= at
            if d.priority is Priority.MARKETING:
                mkt_day += same_day
                mkt_week += week_start < d.at <= at

        if req.priority is Priority.MARKETING:
            if mkt_day >= cfg.marketing_daily_cap:
                return decision.suppress(
                    self.name, f"Marketing limit reached: {mkt_day} offer(s) already sent today."
                )
            if mkt_week >= cfg.marketing_weekly_cap:
                return decision.suppress(
                    self.name, f"Marketing limit reached: {mkt_week} offers in the last 7 days."
                )

        over = None
        if day >= cfg.daily_cap:
            over = f"daily cap of {cfg.daily_cap} reached ({day} alerts today)"
        elif hour >= cfg.hourly_cap:
            over = f"hourly cap of {cfg.hourly_cap} reached ({hour} in the last hour)"
        if over is None:
            return decision

        if req.priority is Priority.MARKETING:
            return decision.suppress(self.name, f"Dropped: {over}. Marketing is cut first.")
        digest = config.rules.digest
        if digest.enabled:
            deliver_at = next_local_time(at, tz, digest.send_at)
            return decision.batch(
                self.name,
                f"Moved to the {format_clock(digest.send_at)} digest: {over}.",
                deliver_at,
            )
        return decision.suppress(self.name, f"Dropped: {over}.")
