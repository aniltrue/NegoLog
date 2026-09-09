"""Compare the estimator with the existing public CUHK helper's counters."""
import json
import math

import pytest

from nenv import Preference
from nenv.OpponentModel import CUHKFrequencyOpponentModel, EstimatedPreference
from agents.CUHKAgent.OpponentBidHistory import OpponentBidHistory


@pytest.fixture
def profile_factory(tmp_path):
    def make(arity=(2, 3)):
        names = [f"issue{i}" for i in range(len(arity))]
        path = tmp_path / "profile.json"
        path.write_text(json.dumps({
            "reservationValue": 0,
            "issueWeights": {name: 1 / len(names) for name in names},
            "issues": {name: {f"value{j}": (j + 1) / size for j in range(size)}
                       for name, size in zip(names, arity)},
        }))
        return Preference(str(path))
    return make


def helper_for(reference):
    helper = OpponentBidHistory()
    helper.initializeDataStructures(reference)
    return helper


def assert_matches_helper(model, helper, reference):
    assert model._bid_history == helper.bidHistory
    assert model._bid_counts == helper.bidCounter
    estimate = model.preference
    assert isinstance(estimate, EstimatedPreference)
    assert sum(estimate[issue] for issue in reference.issues) == pytest.approx(1.)
    for index, issue in enumerate(reference.issues):
        counts = helper.opponentBidsStatisticsForDiscrete[index]
        assert model._value_counts[issue] == counts
        assert estimate[issue] == pytest.approx(1 / len(reference.issues))
        maximum = max(counts.values())
        for value in issue.values:
            expected = counts[value] / maximum if maximum else 1.
            assert estimate[issue, value] == pytest.approx(expected)
    assert all(math.isfinite(estimate.get_utility(bid)) for bid in reference.bids)


def test_initial_uniform_and_unobserved_value_policy(profile_factory):
    reference = profile_factory()
    model = CUHKFrequencyOpponentModel(reference)
    helper = helper_for(reference)
    assert model.name == "CUHK Frequency Model"
    assert_matches_helper(model, helper, reference)
    first = reference.bids[0]
    model.update(first, .1)
    helper.updateOpponentModel(first, reference)
    assert_matches_helper(model, helper, reference)
    for issue in reference.issues:
        for value in issue.values:
            assert model.preference[issue, value] == (1. if value == first[issue] else 0.)


def test_repeats_count_as_observations_but_not_new_history(profile_factory):
    reference = profile_factory()
    model = CUHKFrequencyOpponentModel(reference)
    helper = helper_for(reference)
    for step, index in enumerate([0, 0, 0, 2, 3, 3, 1, 5]):
        bid = reference.bids[index]
        model.update(bid, step / 10)
        helper.updateOpponentModel(bid, reference)
        assert_matches_helper(model, helper, reference)
    assert len(model._bid_history) == 5
    assert sum(model._bid_counts.values()) == 8
    assert model._bid_counts[reference.bids[0]] == 3


def test_public_gate_at_100_distinct_bids_is_not_a_sliding_window(profile_factory):
    reference = profile_factory((11, 10))
    model = CUHKFrequencyOpponentModel(reference)
    helper = helper_for(reference)
    # At 99 and 100 distinct bids, repeated observations still count.
    indices = list(range(99)) + [0, 0, 99, 0, 100, 0, 101]
    frozen_counts = None
    for step, index in enumerate(indices):
        bid = reference.bids[index]
        model.update(bid, step / len(indices))
        helper.updateOpponentModel(bid, reference)
        assert_matches_helper(model, helper, reference)
        if step == 102:
            assert len(model._bid_history) == 100
            frozen_counts = [dict(counts) for counts in helper.opponentBidsStatisticsForDiscrete]
            assert all(sum(counts.values()) == 103 for counts in frozen_counts)
        elif step > 102:
            assert helper.opponentBidsStatisticsForDiscrete == frozen_counts
    assert len(model._bid_history) == 102
    assert sum(model._bid_counts.values()) == len(indices)
    assert model._bid_counts[reference.bids[0]] == 5


def test_single_value_domain_and_utility_metrics(profile_factory):
    reference = profile_factory((1,))
    model = CUHKFrequencyOpponentModel(reference)
    helper = helper_for(reference)
    for step in range(105):
        model.update(reference.bids[0], step / 105)
        helper.updateOpponentModel(reference.bids[0], reference)
    assert_matches_helper(model, helper, reference)
    assert model._value_counts[reference.issues[0]]["value0"] == 105
    rmse, spearman, kendall = model.calculate_error(reference)
    assert rmse == 0.
    assert math.isnan(spearman) and math.isnan(kendall)


def test_observations_are_snapshots_of_mutable_bids(profile_factory):
    reference = profile_factory()
    model = CUHKFrequencyOpponentModel(reference)
    bid = reference.bids[0].copy()
    first_value = bid[reference.issues[0]]
    model.update(bid, 0.)
    bid[reference.issues[0]] = next(value for value in reference.issues[0].values if value != first_value)
    assert model._bid_history[0][reference.issues[0]] == first_value
    assert sum(model._bid_counts.values()) == 1
    assert model._value_counts[reference.issues[0]][first_value] == 1


def test_base_deadline_contract_does_not_change_frequency_counting(profile_factory):
    reference = profile_factory()
    model = CUHKFrequencyOpponentModel(reference)
    assert model.deadline_round == 1000
    model.set_deadline(2)
    assert model.deadline_round == 2
    for step in range(4):
        model.update(reference.bids[0], step / 4)
    assert model._bid_counts[reference.bids[0]] == 4
