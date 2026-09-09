"""Validated, immutable additive preferences for discrete negotiation domains."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

Bid = Mapping[str, str]


class Preference:
    """An additive utility profile; constructing it never enumerates bids.

    Issue weights must sum to one. Values and reservation utility lie in [0, 1].
    Insertion order is retained because it resolves otherwise equal rankings.
    """

    def __setattr__(self, name, value):
        if getattr(self, "_sealed", False):
            raise AttributeError("Preference is immutable; construct a new profile instead")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if getattr(self, "_sealed", False):
            raise AttributeError("Preference is immutable; construct a new profile instead")
        object.__delattr__(self, name)

    def __init__(self, issue_weights: Mapping[str, float],
                 value_weights: Mapping[str, Mapping[str, float]],
                 reservation: float = 0.0):
        if not isinstance(issue_weights, Mapping) or not isinstance(value_weights, Mapping):
            raise ValueError("Issue and value weights must be JSON objects / mappings")
        if not issue_weights or set(issue_weights) != set(value_weights):
            raise ValueError("Provide the same nonempty issues in both weight mappings")
        weights = {}
        values = {}
        for issue, weight in issue_weights.items():
            if not isinstance(issue, str) or not issue:
                raise ValueError("Issue names must be nonempty strings")
            weights[issue] = self._unit(weight, "Issue weight")
            if not isinstance(value_weights[issue], Mapping) or not value_weights[issue]:
                raise ValueError(f"Issue {issue!r} must contain a nonempty value-to-utility mapping")
            values[issue] = {}
            for value, utility in value_weights[issue].items():
                if not isinstance(value, str) or not value:
                    raise ValueError("Value names must be nonempty strings")
                values[issue][value] = self._unit(utility, "Value utility")
        if not math.isclose(sum(weights.values()), 1.0, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Issue weights must sum to one")
        self.issue_weights = MappingProxyType(weights)
        self.value_weights = MappingProxyType({
            issue: MappingProxyType(items) for issue, items in values.items()
        })
        self.reservation = self._unit(reservation, "Reservation utility")
        self.issues = tuple(weights)
        self.domain = MappingProxyType({issue: tuple(values[issue]) for issue in weights})
        self._valid_values = {issue: frozenset(items) for issue, items in self.domain.items()}
        self.size = math.prod(len(items) for items in self.domain.values())
        self._sealed = True

    @staticmethod
    def _unit(value: float, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError(f"{name} must be a finite number in [0, 1]")
        # Check bounds before float conversion so oversized JSON integers also
        # produce the documented input error, rather than OverflowError.
        if not 0 <= value <= 1 or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number in [0, 1]")
        return float(value)

    def validate_bid(self, bid: Bid) -> tuple[str, ...]:
        """Validate a complete bid and return its canonical immutable encoding."""
        if not isinstance(bid, Mapping) or set(bid) != set(self.issues):
            raise ValueError("A bid must contain exactly one value for every issue")
        for issue in self.issues:
            if not isinstance(bid[issue], str) or bid[issue] not in self._valid_values[issue]:
                raise ValueError(f"Unknown value for issue {issue!r}: {bid[issue]!r}")
        return tuple(bid[issue] for issue in self.issues)

    def utility(self, bid: Bid) -> float:
        """Evaluate a complete bid in O(number of issues)."""
        self.validate_bid(bid)
        # fsum avoids accumulated error on many-issue domains; the profile's
        # unit-scale contract also clips a possible last-bit overshoot of one.
        return min(1.0, math.fsum(self.issue_weights[i] * self.value_weights[i][bid[i]]
                                 for i in self.issues))

    def best_bid(self) -> dict[str, str]:
        """Return an own-utility maximum without materializing the outcome space."""
        return {i: max(self.domain[i], key=self.value_weights[i].__getitem__) for i in self.issues}

    @classmethod
    def from_dict(cls, data: Mapping) -> Preference:
        """Read the public NegoLog JSON profile schema."""
        if not isinstance(data, Mapping):
            raise ValueError("A profile must be a JSON object / mapping")
        return cls(data["issueWeights"], data["issues"], data.get("reservationValue", 0.0))

    @classmethod
    def from_json(cls, path: str | Path) -> Preference:
        """Load a UTF-8 NegoLog-style profile file."""
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> dict:
        """Return a JSON-serializable snapshot, independent of this object."""
        return {"reservationValue": self.reservation,
                "issueWeights": dict(self.issue_weights),
                "issues": {i: dict(v) for i, v in self.value_weights.items()}}
