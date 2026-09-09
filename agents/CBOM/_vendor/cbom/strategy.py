"""The published CBOM bidding strategy with an actively updated opponent model.

Algorithm 2 and the Hybrid equations are from Keskin, Buzcu and Aydoğan (2023),
doi:10.1007/s10489-023-05001-9. Public SolverAgent supplies the short-history
weights and P3 default; see docs/provenance.md. This is a maintained Python
implementation, not the incomplete legacy Java executable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .model import ConflictBasedOpponentModel
from .preferences import Bid, Preference
from .search import CandidatePool, NoAvailableBid, Selection

# Oldest to newest utility difference. The original three-difference weights
# intentionally sum to .99; normalizing them would change the inherited policy.
BEHAVIOR_WEIGHTS = {
    1: (1.0,),
    2: (0.25, 0.75),
    3: (0.11, 0.22, 0.66),
    4: (0.05, 0.15, 0.3, 0.5),
}


@dataclass(frozen=True)
class Action:
    """A framework-neutral decision and its candidate-selection evidence.

    For acceptance, ``bid`` is the opponent's received offer; ``selection`` records
    the next offer considered by Algorithm 2, when one was available. ``end`` has
    no bid. Utilities are always evaluated from this agent's own preferences.
    """

    kind: Literal["offer", "accept", "end"]
    bid: dict[str, str] | None = None
    own_utility: float | None = None
    target: float | None = None
    selection: Selection | None = None
    reason: str = ""


class CBOMAgent:
    """Combine Hybrid concession, unused candidates and CBOM product selection.

    Call ``receive(bid, t)`` once for each received offer, then ``act(t)`` to
    choose a response. Time must be normalized to [0, 1] and nondecreasing.
    An agent can also start a session by calling ``act(0)``.

    P0/P1/P2 are reported paper values. P3 and the short-history weights come
    from public SolverAgent. ``model_threshold=3`` and ``epsilon=.02`` are
    configurable defaults introduced by this maintained implementation, not
    recovered experimental settings. Domain-size-dependent parameter tuning
    and emotional/sensitivity adaptation are not part of this strategy.
    """

    def __init__(
        self,
        preference: Preference,
        model: ConflictBasedOpponentModel | None = None,
        *,
        p0: float = 0.9,
        p1: float = 0.7,
        p2: float = 0.4,
        p3: float = 0.5,
        model_threshold: int = 3,
        epsilon: float = 0.02,
        mode: str = "auto",
        max_exact_outcomes: int = 50_000,
        sample_size: int = 4096,
        seed: int = 0,
    ):
        self.preference = preference
        self.p0 = Preference._unit(p0, "P0")
        self.p1 = Preference._unit(p1, "P1")
        self.p2 = Preference._unit(p2, "P2")
        self.p3 = Preference._unit(p3, "P3")
        self.epsilon = Preference._unit(epsilon, "Epsilon")
        if (isinstance(model_threshold, bool) or not isinstance(model_threshold, int)
                or model_threshold < 1):
            raise ValueError("model_threshold must be a positive integer")
        self.model_threshold = model_threshold
        self.model = ConflictBasedOpponentModel(preference) if model is None else model
        if dict(self.model.preference.domain) != dict(preference.domain):
            raise ValueError("The opponent model must describe the same domain")
        self.pool = CandidatePool(
            preference, mode=mode, max_exact_outcomes=max_exact_outcomes,
            sample_size=sample_size, seed=seed,
        )
        self._own_history: list[dict[str, str]] = []
        self._own_utilities: list[float] = []
        self._opponent_history: list[dict[str, str]] = []
        self._opponent_utilities: list[float] = []
        self._offered: set[tuple[str, ...]] = set()
        self._last_time = 0.0
        self._terminal = False
        self._pending_offer = False

    @property
    def own_history(self) -> tuple[dict[str, str], ...]:
        """A detached snapshot of offers actually made, excluding acceptances."""
        return tuple(dict(bid) for bid in self._own_history)

    @property
    def opponent_history(self) -> tuple[dict[str, str], ...]:
        """A detached snapshot of the observed opponent offers."""
        return tuple(dict(bid) for bid in self._opponent_history)

    def _event_time(self, t: float) -> float:
        if self._terminal:
            raise RuntimeError("The negotiation has already ended")
        t = Preference._unit(t, "Normalized time")
        if t < self._last_time:
            raise ValueError("Negotiation time must be nondecreasing")
        return t

    def receive(self, bid: Bid, t: float) -> None:
        """Validate and observe one complete offer, updating CBOM immediately.

        The supplied bid is copied. Invalid time or bid input leaves the agent
        and its default model unchanged. Model warm-up controls proposal scoring,
        not observation collection: no early offers are dropped.
        """
        t = self._event_time(t)
        utility = self.preference.utility(bid)
        snapshot = dict(bid)
        self.model.update(snapshot, t)
        self._opponent_history.append(snapshot)
        self._opponent_utilities.append(utility)
        self._last_time = t
        self._pending_offer = True

    def time_based(self, t: float) -> float:
        """The quadratic time component, evaluated without changing state."""
        t = Preference._unit(t, "Normalized time")
        return (1 - t) ** 2 * self.p0 + 2 * (1 - t) * t * self.p1 + t ** 2 * self.p2

    def target_utility(self, t: float) -> float:
        """Hybrid target with reservation and attainable-utility bounds.

        Until there is a previous own offer and two opponent offers, the time
        component alone is used. Otherwise the last four opponent utility
        changes are weighted from oldest to newest, matching public SolverAgent.
        """
        t = Preference._unit(t, "Normalized time")
        target = self.time_based(t)
        if self._own_utilities and len(self._opponent_utilities) >= 2:
            utilities = self._opponent_utilities[-5:]
            differences = [current - previous for previous, current in zip(utilities, utilities[1:])]
            delta = sum(change * weight for change, weight in zip(
                differences, BEHAVIOR_WEIGHTS[len(differences)],
            ))
            behavior = self._own_utilities[-1] - (self.p3 + self.p3 * t) * delta
            target = (1 - t ** 2) * behavior + t ** 2 * target
        maximum = self.preference.utility(self.preference.best_bid())
        return max(self.preference.reservation, min(maximum, target))

    def _can_accept(self, candidate_utility: float | None = None) -> bool:
        if not self._pending_offer:
            return False
        floor_candidates = self._own_utilities.copy()
        if candidate_utility is not None:
            floor_candidates.append(candidate_utility)
        if not floor_candidates:
            return False
        floor = max(self.preference.reservation, min(floor_candidates))
        return self._opponent_utilities[-1] >= floor

    def _accept(self, target: float, selection: Selection | None) -> Action:
        self._terminal = True
        return Action(
            "accept", dict(self._opponent_history[-1]), self._opponent_utilities[-1],
            target, selection, "received offer meets the historical acceptance floor",
        )

    def _end(self, target: float, reason: str) -> Action:
        self._terminal = True
        return Action("end", target=target, reason=reason)

    def act(self, t: float) -> Action:
        """Choose an offer, accept the current received bid, or end the session.

        The opening offer maximizes own utility. Subsequent proposals follow
        Algorithm 2. Acceptance uses the minimum utility among past own offers
        and the next candidate, guarded by reservation utility. Candidate-pool
        exhaustion ends the session unless the received offer meets the historic
        floor; at t=1 an acceptable offer can be accepted, but no new offer is
        sent. These finite-session rules are explicit implementation choices.
        """
        t = self._event_time(t)
        target = self.target_utility(t)
        maximum = self.preference.utility(self.preference.best_bid())
        self._last_time = t
        if maximum < self.preference.reservation:
            return self._end(target, "no outcome meets reservation utility")

        # The paper does not specify how the initiating agent opens a session.
        # Use an own maximum and make that initialization explicit in the trace.
        opening = not self._own_history
        estimated = None
        if not opening and len(self._opponent_history) >= self.model_threshold:
            estimated = self.model.preference
        try:
            selection = self.pool.select(
                maximum if opening else target,
                epsilon=0.0 if opening else self.epsilon,
                excluded=self._offered,
                opponent=estimated,
            )
        except NoAvailableBid:
            if self._can_accept():
                return self._accept(target, None)
            return self._end(target, "candidate pool exhausted")

        if self._can_accept(selection.own_utility):
            return self._accept(target, selection)
        if t == 1.0:
            return self._end(target, "deadline reached")
        if selection.own_utility < self.preference.reservation:
            return self._end(target, "candidate does not meet reservation utility")

        bid = dict(selection.bid)
        self._own_history.append(bid)
        self._own_utilities.append(selection.own_utility)
        self._offered.add(self.preference.validate_bid(bid))
        # A counteroffer declines the received offer. Repeated act() callbacks
        # must not accept that old offer unless it is received again.
        self._pending_offer = False
        return Action(
            "offer", dict(bid), selection.own_utility, target, selection,
            "own-utility opening" if opening else "hybrid candidate selection",
        )
