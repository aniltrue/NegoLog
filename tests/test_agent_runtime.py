"""Regression checks for failures observed in bounded real agent sessions."""
import math
import random
from types import SimpleNamespace

import numpy as np
import pytest

import nenv
from agents import Caduceus, Caduceus2015, IAMhaggler, SAGAAgent
from agents.Caduceus2015.SaneUtilitySpace import SaneUtilitySpace
from agents.RandomDance.RandomDance import PlayerData


@pytest.fixture
def saga():
    preference, _ = nenv.domain_loader("0")
    agent = SAGAAgent(preference, 32, [])
    agent.initiate("Opponent")
    agent.rnd.seed(23)
    return agent


@pytest.mark.parametrize("time", [0., .02, (1 - math.log(2, 3)) / 2, .25, .5, .6])
def test_saga_early_below_target_offer_has_zero_finite_acceptance_probability(saga, time):
    calls = []

    def draw():
        calls.append(True)
        return 0.

    saga.rnd = SimpleNamespace(random=draw)
    with np.errstate(invalid="raise", over="raise"):
        assert not saga.isAcceptable(time, .9, .2)
    assert calls == [True]  # Keep the agent's existing RNG consumption.


def test_saga_low_opening_utility_produces_valid_offer_without_nan(saga):
    worst = saga.preference.bids[-1]
    saga.receive_bid(worst, .02)
    with np.errstate(invalid="raise", over="raise"):
        response = saga.act(.02)
    assert isinstance(response, nenv.Offer)
    assert response.bid in saga.preference.bids
    assert math.isfinite(saga.preference.get_utility(response.bid))
    assert math.isfinite(saga.getTarget(.02))


@pytest.mark.parametrize("draw", [0., .5, .99])
def test_saga_above_target_acceptance_rule_is_unchanged(saga, draw):
    time, target, utility = .2, .8, .95
    expected_probability = ((utility - target) / (1. - target + 1e-10)) ** (3 ** ((.5 - time) * 2))
    saga.rnd = SimpleNamespace(random=lambda: draw)
    assert saga.isAcceptable(time, target, utility) == (draw < expected_probability)


def test_caduceus_utility_space_keeps_inverse_initialization_and_copy_zero_operations():
    reference, _ = nenv.domain_loader("0")
    estimate = SaneUtilitySpace(reference)
    issue_total = sum(1. - reference.issue_weights[issue] for issue in reference.issues)
    for issue in reference.issues:
        assert estimate[issue] == pytest.approx((1. - reference.issue_weights[issue]) / issue_total)
        value_total = sum(1. - reference.value_weights[issue][value] for value in issue.values)
        for value in issue.values:
            assert estimate[issue, value] == pytest.approx((1. - reference.value_weights[issue][value]) / value_total)
    estimate.init_copy(reference)
    assert estimate.issue_weights == reference.issue_weights
    assert estimate.value_weights == reference.value_weights
    estimate.init_zero()
    assert all(estimate[issue] == 0 for issue in estimate.issues)
    assert all(estimate[issue, value] == 0 for issue in estimate.issues for value in issue.values)


@pytest.mark.parametrize("agent_class", [Caduceus2015, Caduceus])
def test_caduceus_can_receive_first_offer_and_use_its_late_counter_offer(agent_class):
    reference, _ = nenv.domain_loader("0")
    previous_random = random.getstate()
    previous_numpy = np.random.get_state()
    try:
        random.seed(23)
        np.random.seed(23)
        agent = agent_class(reference, 32, [])
        agent.initiate("Opponent")
        agent.receive_bid(reference.bids[-1], .1)
        response = agent.act(.9)
        assert isinstance(response, (nenv.Offer, nenv.Accept))
        assert response.bid in reference.bids
        assert math.isfinite(reference.get_utility(response.bid))
    finally:
        random.setstate(previous_random)
        np.random.set_state(previous_numpy)


@pytest.mark.parametrize("first_time", [1. / 32, .25, .75])
def test_iamhaggler_first_response_after_slot_zero_waits_for_observed_history(first_time):
    reference, _ = nenv.domain_loader("0")
    agent = IAMhaggler(reference, 32, [])
    agent.initiate("Opponent")
    assert isinstance(agent.act(0.), nenv.Offer)
    agent.receive_bid(reference.bids[-1], first_time)
    response = agent.act(first_time)
    assert isinstance(response, nenv.Offer)
    assert response.bid in reference.bids
    assert agent.previousTargetUtility == pytest.approx(1. - first_time / 2.)
    assert agent.opponentTimes == agent.opponentUtilities == []
    assert agent._gp_X == []

    # A later observed slot closes the first one and enables the existing GP.
    agent.receive_bid(reference.bids[-1], first_time + 1. / 36)
    later = agent.act(first_time + 1. / 36)
    assert isinstance(later, (nenv.Offer, nenv.Accept))
    assert later.bid in reference.bids
    assert len(agent.opponentTimes) == len(agent.opponentUtilities) == 1
    assert len(agent._gp_X) == 1
    assert math.isfinite(agent.previousTargetUtility)
    assert np.isfinite(agent.means).all()
    assert np.isfinite(agent.variances).all()


@pytest.mark.parametrize("domain", ["0", "16"])
def test_randomdance_self_utility_keeps_reference_bids_and_independent_issue_contributions(domain):
    reference, _ = nenv.domain_loader(domain)
    original_bids = [bid.copy() for bid in reference.bids]
    original_utilities = [bid.utility for bid in reference.bids]
    minimum = reference.bids[-1].utility
    model = PlayerData(reference.issues, 1.)

    model.SetMyUtility(reference)

    assert reference.bids == original_bids
    assert [bid.utility for bid in reference.bids] == original_utilities
    for bid in reference.bids:
        assert reference.get_utility(bid) == pytest.approx(bid.utility)
        assert model.GetUtility(bid) == pytest.approx((bid.utility - minimum) / (1. - minimum))
