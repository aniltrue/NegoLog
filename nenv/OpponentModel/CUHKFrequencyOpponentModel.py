# Keep first-line summaries (D212), rather than the conflicting D213 convention.
# noqa: D213
"""Expose the public CUHKAgent helper's frequency counters as an estimator.

The counting rule comes from ``agents/CUHKAgent/OpponentBidHistory.py`` in
NegoLog. It is implemented locally to avoid importing the agent registry from
the environment's opponent-model package.
"""
from nenv.Bid import Bid
from nenv.Preference import Preference
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.OpponentModel.EstimatedPreference import EstimatedPreference


class CUHKFrequencyOpponentModel(AbstractOpponentModel):  # noqa: D213
    """An opt-in preference view of the public CUHK value-frequency rule.

    Every offer increments its bid count. Value counts include repeated offers
    while the history contains at most 100 distinct bids. The 101st distinct
    bid stops subsequent value-count updates, including repeats; the distinct
    history itself continues growing. This preserves the helper's existing
    gate, rather than introducing a sliding window.

    The helper does not learn issue weights. This adapter uses equal issue
    weights and divides each issue's value counts by their maximum. Before any
    observations all values have utility 1; after observations, unseen values
    have utility 0. These are explicit adapter policies, not CUHKAgent's full
    bid-selection or acceptance strategy. Per-issue normalization can rank bids
    differently from the helper's sum of raw frequencies.

    CUHKAgent reference retained from the public implementation:
    Hao, J., Leung, Hf. (2014). CUHKAgent: An Adaptive Negotiation Strategy for
    Bilateral Negotiations over Multiple Items. Studies in Computational
    Intelligence, vol 535. https://doi.org/10.1007/978-4-431-54758-7_11
    """

    def __init__(self, reference: Preference):
        """Initialize uniform estimates and empty bid and value counters."""
        super().__init__(reference)
        self._bid_history = []
        self._bid_counts = {}
        self._value_counts = {
            issue: {value: 0 for value in issue.values}
            for issue in self._pref.issues
        }

    @property
    def name(self) -> str:
        return "CUHK Frequency Model"

    def update(self, bid: Bid, t: float):  # noqa: D213
        """Count an offer using the public helper's 100-distinct-bid gate.

        The received bid is copied so later caller mutation cannot alter an
        observation. The frequency rule does not use negotiation time ``t``.
        """
        observation = bid.copy()
        if observation not in self._bid_history:
            self._bid_history.append(observation)
        self._bid_counts[observation] = self._bid_counts.get(observation, 0) + 1

        if len(self._bid_history) <= 100:
            for issue in self._pref.issues:
                self._value_counts[issue][observation[issue]] += 1

    @property
    def preference(self) -> EstimatedPreference:
        """Return equal issue weights and max-normalized observed frequencies."""
        for issue in self._pref.issues:
            self._pref[issue] = 1.
            for value in issue.values:
                self._pref[issue, value] = float(self._value_counts[issue][value])
        self._pref.normalize()
        return self._pref
