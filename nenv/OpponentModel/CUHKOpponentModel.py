# Keep the first-line summary (D212), rather than the conflicting D213 convention.
# noqa: D213
"""Estimate opponent preferences from CUHK-style value frequencies.

A standalone implementation of the frequency-based opponent modeling approach used by CUHKAgent.
Tracks value frequencies from opponent bids and estimates opponent preferences.

Based on: Hao, J., Leung, Hf. (2014). CUHKAgent: An Adaptive Negotiation Strategy for
Bilateral Negotiations over Multiple Items. ANAC 2012 Winner.
"""

from typing import List, Dict
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.Preference import Preference
from nenv.Bid import Bid


class CUHKOpponentModel(AbstractOpponentModel):
    """
    Frequency-based opponent model that tracks how often each value appears in opponent bids.

    Uses a frequency heuristic: values that appear more frequently are assumed
    to be more important to the opponent.
    """

    # Keep the established attribute names for existing model integrations.
    _bidHistory: List[Bid]  # noqa: N815
    _opponentBidsStatisticsForDiscrete: List[Dict[str, int]]  # noqa: N815

    def __init__(self, reference: Preference):
        """
        Initialize the CUHK opponent model.

        :param reference: Reference preference to get domain information
        """
        super().__init__(reference)

        self._bidHistory = []
        self._opponentBidsStatisticsForDiscrete = []

        # Initialize frequency counters for all issues and values
        # Zero counts normalize to equal value weights until offers arrive.
        for issue in reference.issues:
            self._opponentBidsStatisticsForDiscrete.append(
                {value: 0 for value in issue.values}
            )

        # Initialize EstimatedPreference with uniform weights
        # (Will be updated as we observe opponent bids)
        for issue in self._pref.issues:
            self._pref[issue] = 1.0 / len(self._pref.issues)
            for value in issue.values:
                self._pref[issue, value] = 1.0

        self._pref.normalize()

    @property
    def name(self) -> str:
        """Return the name of this opponent model."""
        return "CUHK Frequency Opponent Model"

    def update(self, bid: Bid, t: float):
        """
        Update the opponent model with a new bid from the opponent.

        :param bid: Bid received from opponent
        :param t: Current negotiation time (0-1)
        """
        # Add bid to history if not already present
        if bid not in self._bidHistory:
            self._bidHistory.append(bid.copy())

        self._update_statistics(bid)

    def _update_statistics(self, bid: Bid):
        """
        Update frequency counters for each value in the bid.

        :param bid: Bid to update statistics from
        """
        for issue_idx, issue in enumerate(self._pref.issues):
            value = bid[issue]

            if issue_idx < len(self._opponentBidsStatisticsForDiscrete):
                if value in self._opponentBidsStatisticsForDiscrete[issue_idx]:
                    self._opponentBidsStatisticsForDiscrete[issue_idx][value] += 1

    @property
    def preference(self):
        """
        Return the estimated opponent preference based on observed value frequencies.

        :return: EstimatedPreference object with frequency-based weights
        """
        # Update EstimatedPreference based on current frequency statistics
        for issue_idx, issue in enumerate(self._pref.issues):
            # Use uniform issue weights (CUHK model doesn't learn issue weights)
            self._pref[issue] = 1.0 / len(self._pref.issues)

            # Update value weights based on frequencies
            if issue_idx < len(self._opponentBidsStatisticsForDiscrete):
                for value in issue.values:
                    freq = self._opponentBidsStatisticsForDiscrete[issue_idx].get(value, 0)
                    self._pref[issue, value] = float(freq)

        # Normalize to ensure proper weight distributions
        self._pref.normalize()

        return self._pref
