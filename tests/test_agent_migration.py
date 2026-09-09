"""Small deterministic checks of the built-in agents and their helper contracts."""
import importlib
import json
import math
import random

import numpy as np
import pytest

import nenv
from agents import (
    AgentBuyog,
    CUHKAgent,
    HardHeaded,
    HybridAgent,
    HybridAgentWithOppModel,
    IAMhaggler,
    NiceTitForTat,
    PonPokoAgent,
    Rubick,
    SAGAAgent,
)
from agents.AgentBuyog.OpponentInfo import OpponentInfo
from agents.CUHKAgent.OpponentBidHistory import OpponentBidHistory
from agents.HardHeaded.BidHistory import BidHistory
from agents.HardHeaded.BidSelector import BidSelector
from agents.SAGA.GeneticAlgorithm import GeneticAlgorithm
from nenv.OpponentModel import UniformEstimatedPreference


@pytest.fixture
def preference(tmp_path):
    """Nine bids with ties and different value names across the two issues."""
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "reservationValue": 0,
        "issueWeights": {"first": 0.5, "second": 0.5},
        "issues": {
            "first": {"a": 0, "b": 0.5, "c": 1},
            "second": {"x": 0, "y": 0.5, "z": 1},
        },
    }))
    return nenv.Preference(str(path))


def initiate(agent_type, preference, session_time=1000):
    agent = agent_type(preference, session_time, [])
    agent.initiate("Opponent")
    # Per-agent generators are separate from the module-level random generator.
    for value in vars(agent).values():
        if isinstance(value, random.Random):
            value.seed(23)
    return agent


@pytest.mark.parametrize("agent_type", [
    AgentBuyog, CUHKAgent, HardHeaded, HybridAgent, HybridAgentWithOppModel,
    IAMhaggler, NiceTitForTat, PonPokoAgent, Rubick, SAGAAgent,
])
def test_builtin_agent_can_open_and_respond(preference, agent_type):
    random_state = random.getstate()
    numpy_state = np.random.get_state()
    try:
        random.seed(23)
        np.random.seed(23)
        agent = initiate(agent_type, preference)
        opening = agent.act(0.0)
        assert isinstance(opening, nenv.Offer)
        assert opening.bid in preference.bids

        # Stay inside the opening time slot; no regression fit is required.
        agent.receive_bid(preference.bids[-1], 0.01)
        response = agent.act(0.02)
        assert isinstance(response, (nenv.Offer, nenv.Accept))
        assert response.bid in preference.bids
        assert math.isfinite(preference.get_utility(response.bid))
    finally:
        random.setstate(random_state)
        np.random.set_state(numpy_state)


@pytest.mark.parametrize("discount, time", [(1.0, 0.5), (0.9, 0.2), (0.9, 0.8)])
def test_cuhk_small_domain_concession_and_discount_branches(preference, discount, time):
    agent = initiate(CUHKAgent, preference)
    agent.discountingFactor = discount
    agent.concedeToDiscountingFactor = 0.5
    agent.reservationValue = 0.2
    agent.opponentBidHistory.updateOpponentModel(preference.bids[-1], preference)

    result = agent.BidToOffer(time)

    if discount == 1.0:
        expected = 1.0 - (1.0 - 0.2) * time ** 2
    elif time <= 0.5:
        minimum = discount / discount ** 0.5
        expected = 1.0 - (1.0 - minimum) * (time / 0.5) ** 2
    else:
        expected = discount / discount ** time
    assert agent.utilityThreshold == pytest.approx(expected)
    assert result in preference.bids


def test_cuhk_action_uses_the_supplied_normalized_time(preference):
    agent = initiate(CUHKAgent, preference)
    agent.act(0.125)
    assert agent.timeLeftBefore == agent.timeLeftAfter == 0.125
    assert agent.maximumTimeOwn == 0


@pytest.mark.parametrize("candidate_count", [199, 200, 201])
def test_cuhk_candidate_sampling_is_with_replacement(preference, monkeypatch, candidate_count):
    calls = []

    class AlwaysFirstRandom:
        def randint(self, low, high):
            calls.append((low, high))
            return low

        def random(self):
            return 0.0

        def choice(self, values):
            return values[0]

    module = importlib.import_module("agents.CUHKAgent.OpponentBidHistory")
    monkeypatch.setattr(module.random, "Random", AlwaysFirstRandom)
    history = OpponentBidHistory()
    history.initializeDataStructures(preference)
    best, worst = preference.bids[0], preference.bids[-1]
    history.updateOpponentModel(best, preference)
    candidates = [worst] * (candidate_count - 1) + [best]

    chosen = history.ChooseBid(candidates, preference)

    assert candidates[-1] == best  # The caller's list is not replaced or shuffled.
    if candidate_count < 200:
        assert calls == []
        assert chosen == best
    else:
        assert calls == [(0, candidate_count - 1)] * 200
        assert chosen == worst  # Repeated draws can omit the unique best bid.


def test_hardheaded_issue_indices_and_learning_are_paired(preference):
    agent = initiate(HardHeaded, preference)
    first = preference.bids[-1].copy()
    second = first.copy()
    second[preference.issues[1]] = "z"
    assert BidHistory(preference).BidDifference(first, second) == {0: 0, 1: 1}

    agent.receive_bid(first, 0.1)
    agent.receive_bid(second, 0.2)

    assert isinstance(agent.oppUtility, UniformEstimatedPreference)
    assert agent.oppUtility[preference.issues[0]] == pytest.approx(0.6 / 1.1)
    assert agent.oppUtility[preference.issues[1]] == pytest.approx(0.5 / 1.1)
    assert agent.oppUtility[preference.issues[1], "z"] == pytest.approx(1.0)


def test_hardheaded_bid_selector_retains_all_combinations_and_ties(preference):
    selector = BidSelector(preference)
    assert len(selector.BidList) == 9
    assert set(selector.BidList.values()) == set(preference.bids)
    # Distinct utility keys retain all bids even when actual utilities tie.
    assert sum(preference.get_utility(bid) == 0.5 for bid in selector.BidList.values()) == 3


@pytest.mark.parametrize("duration, expected_utilities", [(300, {0.75, 0.5}), (10000, {0.75})])
def test_hardheaded_duration_changes_the_bid_search_window(preference, monkeypatch, duration, expected_utilities):
    agent = initiate(HardHeaded, preference, duration)
    assert agent.UTILITY_TOLERANCE == pytest.approx(100 / duration)
    agent.act(0.0)
    agent.receive_bid(preference.bids[-1], 0.1)
    monkeypatch.setattr(agent, "get_p", lambda t: 0.1)

    action = agent.act(0.2)

    selected = [action.bid] + [bid for _, bid in agent.offerQueue]
    assert {preference.get_utility(bid) for bid in selected} == expected_utilities


def test_hardheaded_fallback_uses_its_float_random_stream(preference, monkeypatch):
    agent = initiate(HardHeaded, preference)
    opening = agent.act(0.0)
    agent.receive_bid(preference.bids[-1], 0.1)
    calls = []

    def draw():
        calls.append(True)
        return 0.25

    monkeypatch.setattr(agent.random100, "random", draw)
    monkeypatch.setattr(agent.random100, "choice", lambda values: pytest.fail("Unexpected discrete RNG draw"))
    monkeypatch.setattr(agent, "get_p", lambda t: 1.0)

    action = agent.act(0.2)

    assert calls == [True]
    assert action.bid == opening.bid


def test_hybrid_concession_curve_uses_the_updated_parameters(preference):
    agent = initiate(HybridAgent, preference)
    assert (agent.p1, agent.p2) == (0.8, 0.6)
    assert agent.time_based(0.5) == pytest.approx(0.8)
    assert agent.time_based(1.0) == pytest.approx(0.6)


@pytest.mark.parametrize("domain_size, p2, window", [
    (449, 0.8, 0.1), (450, 0.775, 0.09), (1499, 0.775, 0.09),
    (1500, 0.75, 0.08), (4499, 0.75, 0.08), (4500, 0.725, 0.07),
    (17999, 0.725, 0.07), (18000, 0.70, 0.06), (32999, 0.70, 0.06),
    (33000, 0.675, 0.05),
])
def test_hybrid_opponent_variant_domain_boundaries(preference, domain_size, p2, window):
    # Only the length used by initiation is varied; do not build a large domain.
    preference._bids = [preference.bids[0]] * domain_size
    agent = initiate(HybridAgentWithOppModel, preference)
    assert agent.p2 == p2
    assert agent.window_lower_bound == agent.window_upper_bound == window
    assert agent.time_based(1.0) == pytest.approx(p2)


def test_hybrid_opponent_variant_preserves_reservation_floor(preference):
    preference._reservation_value = 0.9
    agent = initiate(HybridAgentWithOppModel, preference)
    assert agent.p2 == 0.9


def test_nice_tit_for_tat_checks_acceptance_permission_first(preference, monkeypatch):
    agent = initiate(NiceTitForTat, preference)
    agent.act(0.0)
    agent.receive_bid(preference.bids[-1], 0.1)
    monkeypatch.setattr(agent, "can_accept", lambda: False)
    monkeypatch.setattr(agent, "isAcceptable", lambda *args: pytest.fail("Acceptance check without permission"))
    assert isinstance(agent.act(0.2), nenv.Offer)


def test_nice_tit_for_tat_updates_nash_on_every_eligible_turn(preference, monkeypatch):
    agent = initiate(NiceTitForTat, preference)
    agent.receive_bid(preference.bids[-1], 0.1)
    agent.myNashUtility = 0.7
    monkeypatch.setattr(agent.random100, "random", lambda: 0.99)
    update = agent.update_my_nash_utility
    calls = []

    def record_update():
        calls.append(True)
        return update()

    monkeypatch.setattr(agent, "update_my_nash_utility", record_update)
    agent.chooseCounterBid(0.2)
    agent.chooseCounterBid(0.3)
    assert calls == [True, True]
    agent.chooseCounterBid(1.0)
    assert calls == [True, True]  # The original deadline guard still applies.


@pytest.mark.parametrize("pattern", range(5))
def test_ponpoko_selects_exactly_five_patterns(preference, monkeypatch, pattern):
    calls = []

    def choose_pattern(low, high):
        calls.append((low, high))
        return pattern

    module = importlib.import_module("agents.PonPoko.PonPoko")
    monkeypatch.setattr(module.random, "randint", choose_pattern)
    agent = initiate(PonPokoAgent, preference)
    assert calls == [(0, 4)]
    assert agent.pattern == pattern
    assert isinstance(agent.act(0.0), nenv.Offer)


def test_iamhaggler_resets_discount_at_initiation(preference):
    agent = IAMhaggler(preference, 1000, [])
    agent.discounting_factor = 0.7
    agent.initiate("Opponent")
    assert agent.discounting_factor == 1.0
    assert agent.lastTimeSlot == -1
    assert isinstance(agent.act(0.0), nenv.Offer)


def test_buyog_initializes_a_concrete_uniform_preference(preference):
    info = OpponentInfo("Opponent", preference)
    assert isinstance(info.pref, UniformEstimatedPreference)
    for issue in preference.issues:
        assert info.pref[issue] == pytest.approx(0.5)
        assert all(info.pref[issue, value] == 1.0 for value in issue.values)


def test_saga_random_preferences_and_children_use_the_concrete_type(preference):
    algorithm = GeneticAlgorithm(preference, pop_size=2, max_generation=1)
    algorithm.rnd.seed(23)
    parent1 = algorithm.random_preference()
    parent2 = algorithm.random_preference()
    child = algorithm.cross_over(parent1, parent2)

    for result in (parent1, parent2, child):
        assert isinstance(result, UniformEstimatedPreference)
        assert all(math.isfinite(result.get_utility(bid)) for bid in preference.bids)
    for parent in (parent1, parent2):
        assert sum(parent[issue] for issue in parent.issues) == pytest.approx(1.0)
    assert preference.bids[0].utility == 1.0
    assert preference.bids[-1].utility == 0.0
