"""Keep tied and single-issue preferences usable by existing models and agents."""
import json
import math
import random

import numpy as np
import pytest

import nenv
from agents import Caduceus, Caduceus2015, RandomDance
from agents.Caduceus2015.SaneUtilitySpace import SaneUtilitySpace
from agents.RandomDance.RandomDance import PlayerData
from nenv.OpponentModel import BayesianOpponentModel


@pytest.fixture
def profile_factory(tmp_path):
    """Provide isolated single-issue and constant preference files."""
    def make(constant=False):
        """Build a loadable preference with the selected degenerate shape."""
        profile = (
            {"reservationValue": 0., "issueWeights": {"x": .5, "y": .5},
             "issues": {"x": {"a": 1., "b": 1.}, "y": {"c": 1., "d": 1.}}}
            if constant else
            {"reservationValue": 0., "issueWeights": {"x": 1.},
             "issues": {"x": {"a": 1., "b": .2}}}
        )
        path = tmp_path / ("constant.json" if constant else "one_issue.json")
        path.write_text(json.dumps(profile))
        return nenv.Preference(str(path))
    return make


def test_bayesian_normalization_uses_bounds_from_current_observations():
    """Recompute Bayesian utility bounds after each new observation."""
    reference, _ = nenv.domain_loader("0")
    model = BayesianOpponentModel(reference)
    before = [model.getNormalizedUtility(bid) for bid in reference.bids]
    assert min(before) == pytest.approx(0.)
    assert max(before) == pytest.approx(1.)
    for step, bid in enumerate(reference.bids[:3]):
        model.update(bid, step / 10)
        utilities = [model.getExpectedUtility(candidate) for candidate in reference.bids]
        expected = [(u - min(utilities)) / (max(utilities) - min(utilities))
                    for u in utilities]
        actual = [model.getNormalizedUtility(candidate) for candidate in reference.bids]
        assert actual == pytest.approx(expected)
        assert all(0. <= value <= 1. for value in actual)
    previous_bounds = model.minUtility, model.maxUtility
    history_size = len(model.fBiddingHistory)
    model.update(reference.bids[0], .9)
    assert (model.minUtility, model.maxUtility) == previous_bounds
    assert len(model.fBiddingHistory) == history_size


def test_reading_initial_tied_bayesian_utilities_does_not_disable_learning(profile_factory):
    """Keep Bayesian learning active after reading initially tied utilities."""
    reference = profile_factory()
    model = BayesianOpponentModel(reference)
    control = BayesianOpponentModel(reference)
    assert [model.getNormalizedUtility(bid) for bid in reference.bids] == [0., 0.]
    assert not model.isCrashed()
    for step, bid in enumerate(reference.bids):
        model.update(bid, step / 10)
        control.update(bid, step / 10)
    assert len(model.fBiddingHistory) == len(reference.bids)
    assert model.fWeightHyps == control.fWeightHyps
    assert model.fEvaluatorHyps == control.fEvaluatorHyps
    assert model.fPreviousBidUtility == control.fPreviousBidUtility


@pytest.mark.parametrize("constant", [False, True])
def test_sane_normalization_handles_zero_totals_and_keeps_sum_convention(profile_factory, constant):
    """Normalize zero totals uniformly while retaining sum-normalized weights."""
    reference = profile_factory(constant)
    model = SaneUtilitySpace(reference)
    assert sum(model.issue_weights.values()) == pytest.approx(1.)
    for issue in model.issues:
        assert sum(model.value_weights[issue].values()) == pytest.approx(1.)
        assert all(math.isfinite(value) and value >= 0
                   for value in model.value_weights[issue].values())
    if not constant:
        assert model["x"] == 1.
        assert model["x", "a"] == 0.
        assert model["x", "b"] == 1.
    model.init_copy(reference)
    assert model.issue_weights == reference.issue_weights
    assert model.value_weights == reference.value_weights
    model.init_zero()
    assert all(weight == 0. for weight in model.issue_weights.values())
    model.normalize()
    for issue in model.issues:
        assert model[issue] == pytest.approx(1. / len(model.issues))
        assert list(model.value_weights[issue].values()) == pytest.approx(
            [1. / len(issue.values)] * len(issue.values))


def test_randomdance_constant_self_model_is_finite_and_does_not_modify_bids(profile_factory):
    """Handle a constant self-model without changing bids or consuming randomness."""
    reference = profile_factory(constant=True)
    original_bids = [bid.copy() for bid in reference.bids]
    data = PlayerData(reference.issues, 1.)
    state = random.getstate()
    data.SetMyUtility(reference)
    assert random.getstate() == state
    assert reference.bids == original_bids
    assert [bid.utility for bid in reference.bids] == [1.] * len(original_bids)
    assert [data.GetUtility(bid) for bid in reference.bids] == pytest.approx(
        [1.] * len(reference.bids))


@pytest.mark.parametrize("agent_class", [Caduceus2015, Caduceus, RandomDance])
@pytest.mark.parametrize("constant", [False, True])
def test_existing_agents_handle_single_issue_and_constant_preferences(profile_factory, agent_class, constant):
    """Exercise existing agent offers on valid single-issue and constant domains."""
    reference = profile_factory(constant)
    random_state = random.getstate()
    numpy_state = np.random.get_state()
    try:
        random.seed(23)
        np.random.seed(23)
        agent = agent_class(reference, 32, [])
        agent.initiate("Opponent")
        opening = agent.act(0.)
        agent.receive_bid(reference.bids[-1], .1)
        response = agent.act(.9)
        for action in (opening, response):
            assert isinstance(action, (nenv.Offer, nenv.Accept))
            assert action.bid in reference.bids
            assert math.isfinite(reference.get_utility(action.bid))
    finally:
        random.setstate(random_state)
        np.random.set_state(numpy_state)
