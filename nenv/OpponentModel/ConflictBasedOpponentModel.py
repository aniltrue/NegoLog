from typing import List, Dict, Tuple, Optional, Any
from functools import cmp_to_key
from collections import deque
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.Preference import Preference
from nenv.Bid import Bid

class ConflictBasedOpponentModel(AbstractOpponentModel):
    """
    **Conflict-based opponent model**:
    Uses stored offer comparisons and majority ordering to estimate preferences.
    Ordinal issue orders are mapped to normalized rank-sum weights.

    Based on conflict-based opponent modeling described by Keskin, M.O., Buzcu, B.
    and Aydogan, R. (2023), Applied Intelligence 53, 29741-29757.
    https://doi.org/10.1007/s10489-023-05001-9

    Key Features:
    *   **Comparison Map (CM)**: Persistently stores all historical offer comparisons.
    *   **Conflict Extraction**: Recalculates conflicts from the full history at every step.
    *   **Majority Rule**: Updates beliefs based on the majority of accumulated evidence.
    """

    def __init__(self, reference: Preference):
        super().__init__(reference, mode='cbom')

        # Domain info extracted from reference preference
        self.domain: Dict[str, List[str]] = {
            issue.name: list(issue.values) for issue in self.preference.issues
        }

        # O: Offer history (deque for sliding window)
        self.max_history_size = 1000
        self.opponent_offer_history: deque[Dict[str, str]] = deque(maxlen=self.max_history_size)

        # CM: Comparison Map.
        # Stores list of (old_offer, new_offer, diffs)
        self.CM: List[Tuple[Dict[str, str], Dict[str, str], List[Tuple[str, str, str]]]] = []

        # Beliefs
        self.value_ordering: Dict[str, List[str]] = {}
        self.issue_ordering: List[str] = []

        # Initialize beliefs based on agent's inverse preferences
        self._initialize_beliefs_from_agent()

        # Initial utility estimation
        self._estimateOppUtilitySpace()

    @property
    def name(self) -> str:
        return "Conflict-Based Opponent Model"

    def update(self, bid: Bid, t: float):
        """
        Update the model with a new bid from the opponent.
        """
        # Convert Bid to simple dict (Offer)
        new_offer = {issue.name: str(bid[issue]) for issue in self.preference.issues}

        # 1. Update History and Comparison Map (CM)
        # Compare NEW offer against all OLD offers in history
        for old_offer in self.opponent_offer_history:
            diffs = self._find_differences(old_offer, new_offer)
            if diffs:
                self.CM.append((old_offer, new_offer, diffs))

        # Add new offer to history
        self.opponent_offer_history.append(new_offer)

        # 2. Extract Conflicts (AC)
        # Re-calculate counts from the full Comparison Map
        vc_counts: Dict[str, Dict[Tuple[str, str], int]] = {
            issue: {} for issue in self.domain
        }
        ic_counts: Dict[Tuple[str, str], int] = {}

        for _old_offer, _current_offer, diffs in self.CM:
            # Single-issue difference: Strong evidence for value preference
            if len(diffs) == 1:
                issue, v_old, v_new = diffs[0]
                # Evidence: v_old > v_new (Concession Assumption)
                self._increment_vc(vc_counts, issue, v_old, v_new)

            # Multi-issue difference: Evidence for issue importance
            elif len(diffs) > 1:
                gains: List[str] = []
                losses: List[str] = []

                for issue, v_old, v_new in diffs:
                    # Check if v_old > v_new (Loss) or v_new > v_old (Gain) according to CURRENT belief
                    if self._is_preferred(issue, v_old, v_new):
                        losses.append(issue)
                    elif self._is_preferred(issue, v_new, v_old):
                        gains.append(issue)

                # Concession Assumption: Total Losses > Total Gains
                # Implies Issues in Losses are more important than Issues in Gains
                for loss_issue in losses:
                    for gain_issue in gains:
                        self._increment_ic(ic_counts, loss_issue, gain_issue)

        # 3. Update Value Ordering (Majority Rule)
        new_value_ordering = {}
        for issue in self.domain:
            values = list(self.domain[issue])

            def compare_values(v1: str, v2: str) -> int:
                # Count(v1 > v2)
                c1 = vc_counts[issue].get((v1, v2), 0)
                # Count(v2 > v1)
                c2 = vc_counts[issue].get((v2, v1), 0)

                if c1 > c2:
                    return 1 # v1 > v2
                elif c2 > c1:
                    return -1 # v2 > v1
                else:
                    # Tie-breaker: Stick to previous belief
                    idx1 = self._get_rank(issue, v1)
                    idx2 = self._get_rank(issue, v2)
                    return 1 if idx1 > idx2 else -1

            # Sort: Smallest to Largest (Least Preferred to Most Preferred)
            # cmp returns 1 if v1 > v2. sorted() expects -1 if v1 < v2.
            # So if v1 > v2, we want v1 later.
            sorted_vals = sorted(values, key=cmp_to_key(compare_values))
            new_value_ordering[issue] = sorted_vals

        self.value_ordering = new_value_ordering

        # 4. Update Issue Ordering (Majority Rule)
        issues = list(self.domain.keys())

        def compare_issues(i1: str, i2: str) -> int:
            # Count(i1 > i2)
            c1 = ic_counts.get((i1, i2), 0)
            # Count(i2 > i1)
            c2 = ic_counts.get((i2, i1), 0)

            if c1 > c2:
                return 1 # i1 > i2
            elif c2 > c1:
                return -1 # i2 > i1
            else:
                # Tie-breaker: Previous belief
                idx1 = self._get_issue_rank(i1)
                idx2 = self._get_issue_rank(i2)
                return 1 if idx1 > idx2 else -1

        self.issue_ordering = sorted(issues, key=cmp_to_key(compare_issues))

        # 5. Estimate Utility Space
        self._estimateOppUtilitySpace()

    # --- Helpers ---

    def _find_differences(self, offer1: Dict[str, str], offer2: Dict[str, str]) -> List[Tuple[str, str, str]]:
        """Returns list of (issue, val_in_offer1, val_in_offer2) for differing issues."""
        diffs = []
        for issue in self.domain:
            v1 = offer1.get(issue)
            v2 = offer2.get(issue)
            if v1 != v2 and v1 is not None and v2 is not None:
                diffs.append((issue, v1, v2))
        return diffs

    def _increment_vc(self, counts: Dict[str, Dict[Tuple[str, str], int]], issue: str, v_preferred: str, v_less: str):
        """Increments the count for v_preferred > v_less."""
        pair = (v_preferred, v_less)
        counts[issue][pair] = counts[issue].get(pair, 0) + 1

    def _increment_ic(self, counts: Dict[Tuple[str, str], int], i_preferred: str, i_less: str):
        """Increments the count for i_preferred > i_less."""
        pair = (i_preferred, i_less)
        counts[pair] = counts.get(pair, 0) + 1

    def _is_preferred(self, issue: str, v_a: str, v_b: str) -> bool:
        """Returns True if v_a is preferred over v_b according to current beliefs."""
        rank_a = self._get_rank(issue, v_a)
        rank_b = self._get_rank(issue, v_b)
        return rank_a > rank_b

    def _get_rank(self, issue: str, value: str) -> int:
        """Returns rank of value (higher is better). Returns -1 if not found."""
        try:
            return self.value_ordering[issue].index(value)
        except (KeyError, ValueError):
            return -1

    def _get_issue_rank(self, issue: str) -> int:
        """Returns rank of issue (higher is better)."""
        try:
            return self.issue_ordering.index(issue)
        except ValueError:
            return -1

    def _initialize_beliefs_from_agent(self):
        """
        Initialize opponent beliefs by inverting agent's preferences.
        """
        agent_value_weights = self.preference._value_weights
        agent_issue_weights = self.preference._issue_weights

        # Initialize value orderings
        self.value_ordering = {}
        for issue in self.preference.issues:
            # Sort values by agent's utility (highest first)
            value_utils = agent_value_weights.get(issue, {})
            sorted_vals = sorted(issue.values, key=lambda v: value_utils.get(v, 0.0), reverse=True)
            # Reverse to get opponent's initial belief (inverse of agent)
            sorted_vals.reverse()
            self.value_ordering[issue.name] = sorted_vals

        # Initialize issue ordering
        sorted_issues = sorted(self.preference.issues,
                             key=lambda i: agent_issue_weights.get(i, 0.0),
                             reverse=True)
        sorted_issues.reverse()
        self.issue_ordering = [issue.name for issue in sorted_issues]

    def _estimateOppUtilitySpace(self):
        """
        Update self._pref using ordinal value weights and normalized issue ranks.
        """
        issue_size = len(self.issue_ordering)

        # Normalize issue ranks by their sum.
        # Rank 1 to n. Weight = Rank / Sum(Ranks).
        # self.issue_ordering is sorted [least_important, ..., most_important]
        issue_weights_map = {}
        total_rank = issue_size * (issue_size + 1) / 2
        if total_rank > 0:
            for idx, issue_name in enumerate(self.issue_ordering):
                # idx 0 -> rank 1
                weight = (idx + 1) / total_rank
                issue_weights_map[issue_name] = weight
        else:
            issue_weights_map = {i: 0.0 for i in self.issue_ordering}

        # Calculate value weights as the one-based rank divided by value count.
        # self.value_ordering is sorted [least_preferred, ..., most_preferred]
        value_weights_map = {}
        for issue_name, values in self.value_ordering.items():
            m = len(values)
            if m > 0:
                # idx 0 (worst) -> 1/m. idx m-1 (best) -> 1.0.
                weights = {}
                for idx, val in enumerate(values):
                    weights[val] = (idx + 1) / m
                value_weights_map[issue_name] = weights
            else:
                value_weights_map[issue_name] = {}

        # Update self._pref (the opponent's estimated preference)
        # Map back to Issue objects
        issue_name_to_obj = {issue.name: issue for issue in self.preference.issues}

        self._pref._value_weights = {
            issue_name_to_obj[issue_name]: weights
            for issue_name, weights in value_weights_map.items()
            if issue_name in issue_name_to_obj
        }

        self._pref._issue_weights = {
            issue_name_to_obj[issue_name]: weight
            for issue_name, weight in issue_weights_map.items()
            if issue_name in issue_name_to_obj
        }
