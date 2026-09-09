"""Check model horizon handoff through the real session manager API."""
import importlib
from types import SimpleNamespace

import pytest

from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.SessionManager import SessionManager


class LegacyConstructorModel(AbstractOpponentModel):
    def __init__(self, reference):
        # A third-party implementation may not call super().__init__.
        self.reference = reference

    @property
    def name(self):
        return "LegacyConstructorModel"

    def update(self, bid, t):
        pass


class RecordingAgent:
    def __init__(self, preference, session_time, estimators):
        self.preference = preference
        self.session_time = session_time
        self.estimators = estimators
        self.initial_horizons = [model.deadline_round for model in estimators]


@pytest.mark.parametrize("seconds,rounds,expected", [(None, 25, 25), (5, 40, 40), (5, None, 1000)])
def test_round_horizon_is_set_before_agent_initialization(monkeypatch, seconds, rounds, expected):
    module = importlib.import_module("nenv.SessionManager")
    prefs = (SimpleNamespace(side="A"), SimpleNamespace(side="B"))
    monkeypatch.setattr(module, "domain_loader", lambda name: prefs)
    monkeypatch.setenv("DEADLINE", "invalid-must-not-be-read")
    session = SessionManager(RecordingAgent, RecordingAgent, "fixture", seconds, rounds,
                             [LegacyConstructorModel], [])
    for side, pref in [(session.agentA, prefs[0]), (session.agentB, prefs[1])]:
        assert side.initial_horizons == [expected]
        assert side.estimators[0].reference is pref
    assert session.agentA.estimators[0] is not session.agentB.estimators[0]


def test_all_models_complete_a_session_with_existing_metric_loggers(tmp_path, monkeypatch):
    import json
    import math
    import nenv
    from nenv.OpponentModel import (
        ClassicFrequencyOpponentModel, WindowedFrequencyOpponentModel,
        BayesianOpponentModel, ConflictBasedOpponentModel, CUHKOpponentModel,
        StepwiseCOMBOpponentModel, ExpectationCOMBOpponentModel,
        RegressionCOMBOpponentModel,
    )
    from nenv.logger.EstimatorMetricLogger import EstimatorMetricLogger
    from nenv.logger.EstimatedParetoLogger import EstimatedParetoLogger
    from nenv.utils.ExcelLog import ExcelLog

    class CyclingAgent(nenv.AbstractAgent):
        @property
        def name(self):
            return "CyclingAgent"

        def initiate(self, opponent_name):
            self.index = 0

        def receive_offer(self, bid, t):
            pass

        def act(self, t):
            bid = self.preference.bids[self.index % len(self.preference.bids)]
            self.index += 1
            return nenv.Offer(bid)

    preferences = []
    for side, values in [("A", {"x": 1., "y": .2}), ("B", {"x": .2, "y": 1.})]:
        path = tmp_path / f"profile{side}.json"
        path.write_text(json.dumps({"reservationValue": 0.,
            "issueWeights": {"color": .7, "size": .3},
            "issues": {"color": values, "size": {"small": .4, "large": 1.}}}))
        preferences.append(nenv.Preference(str(path)))
    module = importlib.import_module("nenv.SessionManager")
    monkeypatch.setattr(module, "domain_loader", lambda name: preferences)
    model_classes = [ClassicFrequencyOpponentModel, WindowedFrequencyOpponentModel,
                     BayesianOpponentModel, ConflictBasedOpponentModel, CUHKOpponentModel,
                     StepwiseCOMBOpponentModel, ExpectationCOMBOpponentModel,
                     RegressionCOMBOpponentModel]
    session = SessionManager(CyclingAgent, CyclingAgent, "fixture", None, 32, model_classes,
                             [EstimatorMetricLogger(str(tmp_path)), EstimatedParetoLogger(str(tmp_path))])
    output = tmp_path / "session.xlsx"
    result = session.run(str(output))
    assert result["TournamentResults"]["Result"] == "Failed"  # valid deadline disagreement
    assert result["TournamentResults"]["Round"] == 32
    workbook = ExcelLog(file_path=str(output))
    for model in session.agentA.estimators:
        assert model.deadline_round == 32
        rows = workbook.log_rows[model.name]
        assert len(rows) == len(workbook.log_rows["Session"])
        assert len(rows) >= 32
        assert all(math.isfinite(row["RMSE_A"]) for row in rows)
        assert all(0 <= row["PrecisionA"] <= 1 for row in rows)
        assert all(0 <= row["RecallA"] <= 1 for row in rows)


@pytest.mark.parametrize("seconds,rounds,expected", [(None, 32, 32), (5, 40, 40), (5, None, 1000)])
def test_embedded_agent_models_receive_the_session_round_limit(tmp_path, monkeypatch, seconds, rounds, expected):
    import json
    import nenv
    from agents.NiceTitForTat.NiceTitForTat import NiceTitForTat
    from agents.HybridAgent.HybridAgentWithOppModel import HybridAgentWithOppModel

    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"reservationValue": 0., "issueWeights": {"color": 1.},
                                "issues": {"color": {"red": 1., "blue": .2}}}))
    module = importlib.import_module("nenv.SessionManager")
    monkeypatch.setattr(module, "domain_loader", lambda name: (nenv.Preference(str(path)), nenv.Preference(str(path))))
    manager = SessionManager(NiceTitForTat, HybridAgentWithOppModel, "fixture", seconds, rounds, [], [])
    for agent in (manager.agentA, manager.agentB):
        agent.initiate("Opponent")
        assert agent.opponent_model.deadline_round == expected


def test_standalone_agents_keep_optional_round_limit_default(tmp_path):
    import json
    import nenv
    from agents.NiceTitForTat.NiceTitForTat import NiceTitForTat
    from agents.HybridAgent.HybridAgentWithOppModel import HybridAgentWithOppModel

    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"reservationValue": 0., "issueWeights": {"color": 1.},
                                "issues": {"color": {"red": 1., "blue": .2}}}))
    for agent_class in (NiceTitForTat, HybridAgentWithOppModel):
        agent = agent_class(nenv.Preference(str(path)), 32, [])
        agent.initiate("Opponent")
        assert agent.deadline_round is None
        assert agent.opponent_model.deadline_round == 1000
