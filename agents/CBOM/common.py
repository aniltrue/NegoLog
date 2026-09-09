"""Lossless conversion between NegoLog's discrete additive profile and CBOM."""

from __future__ import annotations

import nenv

from ._vendor.cbom.preferences import Preference


def profile_snapshot(preference: nenv.Preference) -> Preference:
    """Copy weights without enumerating the domain or mutating the host profile."""
    if type(preference).get_utility is not nenv.Preference.get_utility:
        raise ValueError("CBOM agents require a discrete additive NegoLog utility profile")
    issue_weights = preference.issue_weights
    value_weights = preference.value_weights
    return Preference(
        {issue.name: issue_weights[issue] for issue in preference.issues},
        {issue.name: dict(value_weights[issue]) for issue in preference.issues},
        preference.reservation_value,
    )


class CBOMAdapter(nenv.AbstractAgent):
    """Shared profile and bid conversion; concrete agents implement callbacks."""

    cbom_options: dict = {}

    def _initialize_profile(self) -> None:
        self.cbom_preference = profile_snapshot(self.preference)
        self._pending_bid = None

    @staticmethod
    def _bid_content(bid: nenv.Bid) -> dict[str, str]:
        return {str(issue): value for issue, value in bid}

    def _received(self, bid: nenv.Bid) -> dict[str, str]:
        content = self._bid_content(bid)
        self.cbom_preference.validate_bid(content)
        self._pending_bid = dict(content)
        return content

    def _action(self, result: dict) -> nenv.Action:
        """Validate a core decision, retaining explicit no-agreement semantics."""
        if not isinstance(result, dict):
            raise ValueError("CBOM response must contain an action object")
        kind = result.get("kind")
        if kind == "end":
            self._pending_bid = None
            return nenv.EndNegotiation(result.get("reason", "CBOM ended negotiation"))
        if kind not in ("offer", "accept"):
            raise ValueError("CBOM returned an unknown action kind")
        content = result.get("bid")
        utility = self.cbom_preference.utility(content)
        if utility < self.cbom_preference.reservation:
            raise ValueError("CBOM returned a bid below reservation utility")
        bid = nenv.Bid({issue: content[issue.name] for issue in self.preference.issues})
        bid.utility = self.preference.get_utility(bid)
        if kind == "accept":
            if content != self._pending_bid:
                raise ValueError("CBOM attempted to accept a nonpending offer")
            self._pending_bid = None
            return nenv.Accept(bid)
        self._pending_bid = None
        return nenv.Offer(bid)
