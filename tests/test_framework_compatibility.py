"""Actual public framework integration with legacy model initialization."""
# Pytest assertions are intentional; this rule only recognizes tests importing pytest.
import importlib
import json
from pathlib import Path

import numpy as np

import nenv
from nenv.OpponentModel import (
    BayesianOpponentModel, ClassicFrequencyOpponentModel,
    ConflictBasedOpponentModel, CUHKFrequencyOpponentModel,
    WindowedFrequencyOpponentModel,
)
from nenv.logger.EstimatorMetricLogger import EstimatorMetricLogger
from nenv.logger.EstimatedParetoLogger import EstimatedParetoLogger
from nenv.SessionManager import SessionManager
from nenv.utils.ExcelLog import ExcelLog


class CyclingAgent(nenv.AbstractAgent):
    @property
    def name(self):
        return "Cycler"

    def initiate(self, opponent_name):
        self.index = 0

    def receive_offer(self, bid, t):
        pass

    def act(self, t):
        bid = self.preference.bids[self.index % len(self.preference.bids)]
        self.index += 1
        return nenv.Offer(bid)


def test_sampling_and_wrapper_work_in_public_session_and_round_extractor(tmp_path, monkeypatch):
    preferences = []
    for side, values in [("A", {"x": 1., "y": .2}), ("B", {"x": .2, "y": 1.})]:
        path = tmp_path / f"profile{side}.json"
        path.write_text(json.dumps({"reservationValue": 0.,
            "issueWeights": {"color": .7, "size": .3},
            "issues": {"color": values, "size": {"small": .4, "large": 1.}}}))
        preferences.append(nenv.Preference(str(path)))
    monkeypatch.setattr(importlib.import_module("nenv.SessionManager"), "domain_loader", lambda name: preferences)
    models = [ClassicFrequencyOpponentModel, WindowedFrequencyOpponentModel,
              BayesianOpponentModel, ConflictBasedOpponentModel, CUHKFrequencyOpponentModel]
    logger = EstimatorMetricLogger(str(tmp_path), sample_every=2)
    manager = SessionManager(CyclingAgent, CyclingAgent, "1", None, 6, models,
                             [logger, EstimatedParetoLogger(str(tmp_path))])
    (tmp_path / "sessions").mkdir()
    path = tmp_path / "sessions/Cycler_Cycler_Domain1.xlsx"
    result = manager.run(str(path))
    assert result["TournamentResults"]["Result"] == "Failed"  # nosemgrep: python_assert_rule-assert-used
    assert result["TournamentResults"]["Round"] == 6  # nosemgrep: python_assert_rule-assert-used
    names = [model.name for model in manager.agentA.estimators]
    tournament = ExcelLog(["TournamentResults"])
    tournament.append(result)
    rmse, _spearman, _kendall = logger.get_estimator_results(tournament, names)
    for name in names:
        for round_number in range(6):
            assert bool(rmse[name][round_number]) == (round_number % 2 == 0)  # nosemgrep: python_assert_rule-assert-used
        assert all(np.isfinite(value) for values in rmse[name] for value in values)  # nosemgrep: python_assert_rule-assert-used


def test_environment_uses_this_checkout_and_preexisting_agents_remain_available():
    import agents
    assert Path(nenv.__file__).resolve().parent.parent == Path(__file__).resolve().parents[1]  # nosemgrep: python_assert_rule-assert-used
    for name in ["Rubick", "HardHeaded", "CUHKAgent", "HybridAgent", "HybridAgentWithOppModel",
                 "NiceTitForTat", "IAMhaggler", "PonPokoAgent", "AgentBuyog", "SAGAAgent"]:
        assert getattr(agents, name)  # nosemgrep: python_assert_rule-assert-used
