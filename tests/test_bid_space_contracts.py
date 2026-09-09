"""Lazy bid-space access must represent the complete public domain."""

import math

import pytest

from nenv import EditablePreference
from nenv.BidSpace import BidSpace


@pytest.mark.parametrize("first_access", [len, list])
def test_lazy_bid_space_len_and_iteration_generate_points(first_access):
    """Generate the complete bid space on either first length or iteration access."""
    pref = EditablePreference({"issue": 1.}, {"issue": {"a": 1., "b": .5, "c": .1}})
    space = BidSpace(pref, pref)
    result = first_access(space)
    assert (result if first_access is len else len(result)) == 3
    assert len(space) == 3
    assert [point.bid for point in space] == pref.bids


def test_zero_nash_norm_has_undefined_normalized_balance():
    """Represent normalized balance with a zero Nash norm as undefined."""
    pref = EditablePreference({"issue": 1.}, {"issue": {"a": 1., "b": .5}})
    for issue in pref.issues:
        for value in issue.values:
            pref[issue, value] = 0.
    pref._bids = []
    score = BidSpace(pref, pref).calculate_normalized_balance_score()
    assert math.isnan(score)


def test_nonzero_normalized_balance_formula_is_retained():
    """Preserve the existing normalized balance formula for nonzero Nash norms."""
    pref_a = EditablePreference({"issue": 1.}, {"issue": {"a": 1., "b": .5}})
    pref_b = EditablePreference({"issue": 1.}, {"issue": {"a": .3, "b": 1.}})
    space = BidSpace(pref_a, pref_b)
    nash = space.nash_point
    norm = math.hypot(nash.utility_a, nash.utility_b)
    expected = sum((a.utility - b.utility) * math.hypot(nash.utility_a - a.utility,
                                                      nash.utility_b - b.utility) / (norm + 1e-12)
                   for a, b in zip(pref_a.bids, pref_b.bids))
    assert space.calculate_normalized_balance_score() == pytest.approx(expected)
