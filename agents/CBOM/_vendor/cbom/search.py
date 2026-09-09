"""Finite candidate search with explicit exact and sampled modes."""

from __future__ import annotations

import math
import random
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from itertools import product

from .preferences import Preference


class NoAvailableBid(RuntimeError):
    """Every bid in the configured candidate pool was already offered."""


@dataclass(frozen=True)
class Selection:
    bid: dict[str, str]
    own_utility: float
    opponent_utility: float | None
    epsilon: float
    candidate_count: int
    exact: bool


class CandidatePool:
    """Index a bounded pool once; select within the paper's expanding utility band.

    Exact mode enumerates at most ``max_exact_outcomes`` bids. Auto uses a fixed,
    seeded sample for larger domains. Sampled mode is an approximation to the
    strategy's candidate search, never an approximation to the CBOM update.
    """

    def __init__(self, preference: Preference, mode: str = "auto",
                 max_exact_outcomes: int = 50_000, sample_size: int = 4096,
                 seed: int = 0):
        if not isinstance(mode, str) or mode not in {"auto", "exact", "sampled"}:
            raise ValueError("Search mode must be auto, exact or sampled")
        for name, value in [("max_exact_outcomes", max_exact_outcomes), ("sample_size", sample_size)]:
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        self.preference = preference
        self.exact = mode == "exact" or (mode == "auto" and preference.size <= max_exact_outcomes)
        if self.exact and preference.size > max_exact_outcomes:
            raise ValueError("Exact search exceeds max_exact_outcomes; raise the explicit limit or use sampled")
        if self.exact:
            candidates = product(*preference.domain.values())
        else:
            rng = random.Random(seed)
            # A finite number of draws prevents rejection loops on small domains.
            # Always include the own-utility maximum to provide a feasible opening.
            items = {preference.validate_bid(preference.best_bid()): None}
            for _ in range(sample_size - 1):
                items[tuple(rng.choice(preference.domain[i]) for i in preference.issues)] = None
            candidates = items
        self._entries = []
        for encoded in candidates:
            bid = dict(zip(preference.issues, encoded))
            self._entries.append((preference.utility(bid), encoded))
        # Stable sorting preserves domain insertion order (or seeded draw order) on ties.
        self._entries.sort(key=lambda item: item[0])
        self._utilities = [item[0] for item in self._entries]

    @property
    def size(self) -> int:
        """Actual unique pool size, at most sample_size in sampled mode."""
        return len(self._entries)

    def select(self, target: float, epsilon: float = .02,
               excluded: set[tuple[str, ...]] | None = None,
               opponent: Preference | None = None) -> Selection:
        """Choose max own utility or max utility product in the first nonempty band.

        The initial closed band expands by .01. A direct nearest-distance
        calculation skips empty iterations while preserving this discrete grid.
        Previously offered bids and bids below reservation are never selected.
        """
        target = Preference._unit(target, "Target utility")
        epsilon = Preference._unit(epsilon, "Initial epsilon")
        excluded = excluded or set()
        if opponent is not None and dict(opponent.domain) != dict(self.preference.domain):
            raise ValueError("Opponent profile must have the same ordered domain")
        nearest = math.inf
        for utility, bid in self._entries:
            if bid not in excluded and utility >= self.preference.reservation:
                nearest = min(nearest, abs(utility - target))
        if not math.isfinite(nearest):
            raise NoAvailableBid("No unused bid at or above reservation remains in the candidate pool")
        steps = max(0, math.ceil((nearest - epsilon - 1e-12) / .01))
        width = epsilon + steps * .01
        left = bisect_left(self._utilities, target - width - 1e-12)
        right = bisect_right(self._utilities, target + width + 1e-12)
        selected = None
        best = -math.inf
        count = 0
        for utility, encoded in self._entries[left:right]:
            if encoded in excluded or utility < self.preference.reservation:
                continue
            count += 1
            bid = dict(zip(self.preference.issues, encoded))
            other = opponent.utility(bid) if opponent is not None else None
            score = utility if other is None else utility * other
            if score > best:
                best = score
                selected = (bid, utility, other)
        assert selected is not None
        return Selection(*selected, width, count, self.exact)
