"""CBOM with exact aggregated comparison evidence.

Derived from NegoLog V2's ConflictBasedOpponentModel at c13b4f7 (GPL-3.0).
See NOTICE and docs/method.md for attribution, equivalence scope and assumptions.
"""

from __future__ import annotations

from collections import Counter, deque
from functools import cmp_to_key
from itertools import combinations

from .preferences import Bid, Preference


class ConflictBasedOpponentModel:
    """Estimate ordinal opponent preferences from complete received offers.

    The default history of 1000 controls *new pair creation*. Accumulated evidence
    persists, matching NegoLog V2. Joint transition counters replace stored offer
    pairs without approximating their multiplicity or reinterpreting old evidence.
    """

    def __init__(self, reference: Preference, history_size: int = 1000):
        if isinstance(history_size, bool) or not isinstance(history_size, int) or history_size < 1:
            raise ValueError("history_size must be a positive integer")
        self.reference = reference
        self.history_size = history_size
        self._history: deque[tuple[str, ...]] = deque()
        self._offers: Counter = Counter()
        self._value_counts: Counter = Counter()
        self._joint_counts: Counter = Counter()
        self.observations = 0
        self.comparisons = 0
        # V2 sorts inverse weights ascending, reversing ties in the input order.
        self.value_ordering = {}
        for issue in reference.issues:
            inverse = {v: 1 - reference.value_weights[issue][v] for v in reference.domain[issue]}
            maximum = max(inverse.values())
            inverse = {v: w / maximum if maximum else 1. for v, w in inverse.items()}
            self.value_ordering[issue] = sorted(reversed(reference.domain[issue]), key=inverse.__getitem__)
        inverse_issues = {i: 1 - reference.issue_weights[i] for i in reference.issues}
        total = sum(inverse_issues.values())
        inverse_issues = {i: w / total if total else 1 / len(reference.issues)
                          for i, w in inverse_issues.items()}
        self.issue_ordering = sorted(reversed(reference.issues), key=inverse_issues.__getitem__)
        self._estimate()

    @property
    def preference(self) -> Preference:
        """Current immutable estimated utility profile (higher utility is better)."""
        return self._preference

    @property
    def evidence_cells(self) -> int:
        """Number of occupied evidence counters, not the number of offer pairs."""
        return len(self._value_counts) + len(self._joint_counts)

    def update(self, bid: Bid, t: float | None = None) -> None:
        """Observe one opponent offer. Time is accepted for adapter compatibility.

        Time does not influence CBOM. Invalid bids fail before any state changes.
        """
        new = self.reference.validate_bid(bid)
        for old, count in self._offers.items():
            changes = [(i, a, b) for i, a, b in zip(self.reference.issues, old, new) if a != b]
            if changes:
                self.comparisons += count
            if len(changes) == 1:
                self._value_counts[changes[0]] += count
            else:
                for first, second in combinations(changes, 2):
                    self._joint_counts[first + second] += count
        if len(self._history) == self.history_size:
            expired = self._history.popleft()
            self._offers[expired] -= 1
            if self._offers[expired] == 0:
                del self._offers[expired]
        self._history.append(new)
        self._offers[new] += 1
        self.observations += 1

        # Issue evidence uses the PREVIOUS value beliefs, as in V2. Recompute it
        # after every observation: a changed belief reinterprets historical pairs.
        ranks = {i: {v: k for k, v in enumerate(order)} for i, order in self.value_ordering.items()}
        issue_counts: Counter = Counter()
        for (i, a, b, j, c, d), count in self._joint_counts.items():
            loss_i = ranks[i][a] > ranks[i][b]
            loss_j = ranks[j][c] > ranks[j][d]
            if loss_i != loss_j:
                issue_counts[(i, j) if loss_i else (j, i)] += count

        for issue in self.reference.issues:
            def compare_values(a, b):
                difference = self._value_counts[(issue, a, b)] - self._value_counts[(issue, b, a)]
                if not difference:
                    difference = ranks[issue][a] - ranks[issue][b]
                return (difference > 0) - (difference < 0)
            self.value_ordering[issue] = sorted(self.reference.domain[issue], key=cmp_to_key(compare_values))

        previous = {i: k for k, i in enumerate(self.issue_ordering)}

        def compare_issues(a, b):
            difference = issue_counts[(a, b)] - issue_counts[(b, a)]
            if not difference:
                difference = previous[a] - previous[b]
            return (difference > 0) - (difference < 0)

        self.issue_ordering = sorted(self.reference.issues, key=cmp_to_key(compare_issues))
        self._estimate()

    def _estimate(self) -> None:
        size = len(self.issue_ordering)
        total = size * (size + 1) / 2
        weights = {i: (k + 1) / total for k, i in enumerate(self.issue_ordering)}
        values = {i: {v: (k + 1) / len(order) for k, v in enumerate(order)}
                  for i, order in self.value_ordering.items()}
        # Keep the domain input order stable for interoperable profile exports.
        self._preference = Preference({i: weights[i] for i in self.reference.issues},
                                      {i: {v: values[i][v] for v in self.reference.domain[i]}
                                       for i in self.reference.issues})
