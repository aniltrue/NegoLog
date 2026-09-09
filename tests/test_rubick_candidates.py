"""Opponent value choices must stay within the issue they describe."""
import importlib
import json

import pytest

from agents.Rubick.Rubick import Rubick
from nenv.Preference import Preference


@pytest.fixture
def agent(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "reservationValue": 0,
        "issueWeights": {"first": 0.5, "second": 0.5},
        "issues": {
            "first": {"a": 0, "b": 0.5, "c": 1},
            "second": {"x": 0, "y": 0.5, "z": 1},
        },
    }))
    result = Rubick(Preference(str(path)), session_time=180, estimators=[])
    result.initiate("Opponent")
    return result


def record_choices(monkeypatch):
    choices = []

    def choose_first(candidates):
        choices.append(list(candidates))
        return candidates[0]

    module = importlib.import_module("agents.Rubick.Rubick")
    monkeypatch.setattr(module.random, "choice", choose_first)
    return choices


def test_each_opponent_only_selects_values_from_the_current_issue(agent, monkeypatch):
    agent.frequentValuesList0 = [{"a": 2, "b": 1, "c": 0}, {"x": 3, "y": 1, "z": 0}]
    agent.frequentValuesList1 = [{"a": 0, "b": 1, "c": 3}, {"x": 0, "y": 2, "z": 4}]
    choices = record_choices(monkeypatch)

    agent.extractOpponentPreferences()

    assert choices == [["a", "b"], ["c"], ["x"], ["y", "z"]]
    assert agent.opp0bag == ["a", "x"]
    assert agent.opp1bag == ["c", "y"]


def test_candidate_threshold_uses_the_mean(agent, monkeypatch):
    # Skewed counts distinguish the mean rule from a median rule.
    agent.frequentValuesList0 = [{"a": 0, "b": 0, "c": 9}, {"x": 0, "y": 2, "z": 9}]
    agent.frequentValuesList1 = [{"a": 1, "b": 1, "c": 20}, {"x": 0, "y": 3, "z": 10}]
    choices = record_choices(monkeypatch)

    agent.extractOpponentPreferences()

    assert choices == [["c"], ["c"], ["z"], ["z"]]


@pytest.mark.parametrize("party_count, expected_calls", [(1, 0), (2, 1), (3, 1)])
def test_history_analysis_supports_two_parties(agent, monkeypatch, party_count, expected_calls):
    bid = agent.preference.bids[0]
    agent.history = [bid]
    agent.parties = [f"Party{i}" for i in range(party_count)]
    calls = []
    monkeypatch.setattr(agent, "BidResolver", lambda bid, party: None)
    monkeypatch.setattr(agent, "sortPartyProfiles", lambda party: None)
    monkeypatch.setattr(agent, "analyzeHistory", lambda: calls.append(True))

    agent.receive_offer(bid, 0.5)

    assert len(calls) == expected_calls


def test_mean_handles_an_empty_issue(agent):
    assert agent.mean({}) == 0.0
