"""Preserve published workbook contents and public logger callback contracts."""

import copy
import json
import importlib
import warnings
from types import SimpleNamespace

import pytest
import numpy as np
import pandas as pd

from nenv import Bid, EditablePreference
from nenv.Action import Accept
from nenv.BidSpace import BidSpace
from nenv.SessionLogs import SessionLogs
from nenv.SessionManager import SessionManager
from nenv.logger.AbstractLogger import AbstractLogger
from nenv.logger.EstimatedBidSpaceLogger import EstimatedBidSpaceLogger
from nenv.logger.EstimatedMoveLogger import EstimatedMoveLogger
from nenv.utils.ExcelLog import ExcelLog
from agents import BoulwareAgent, ConcederAgent


def preference(values, reservation=0):
    """Build a one-issue editable preference for logger checks."""
    return EditablePreference({"issue": 1.}, {"issue": values}, reservation)


def agents():
    """Provide two independent agent views with different preferences."""
    return (SimpleNamespace(preference=preference({"a": 1., "b": .2}, .1), estimators=[]),
            SimpleNamespace(preference=preference({"a": .3, "b": 1.}, .2), estimators=[]))


class RecordingLogger(AbstractLogger):
    """Record the terminal result received by the session-end callback."""

    def on_session_end(self, final_row, session):
        """Expose the supplied terminal outcome in a separate result sheet."""
        return {"Recorded": {"Result": final_row["TournamentResults"]["Result"]}}


def workbook(path):
    """Save a minimal real workbook containing one offer."""
    log = ExcelLog(["Session"])
    log.append({"Session": {"Round": 0, "Time": 0., "Who": "A", "Action": "Offer",
                            "BidContent": str(Bid({"issue": "a"}))}})
    log.save(str(path))


@pytest.mark.parametrize("serializer", [repr, json.dumps])
def test_bid_round_trip_preserves_quotes_and_unicode(serializer):
    """Parse quoted and Unicode bid contents from supported serializers."""
    content = {"owner's \"choice\"": "O'Reilly \\ desktop — \"blue\""}
    replay = SessionLogs.__new__(SessionLogs)
    assert replay.parse_bid(serializer(content)).content == content


def test_bid_parser_does_not_evaluate_expressions(tmp_path):
    """Reject executable bid expressions without evaluating their contents."""
    replay = SessionLogs.__new__(SessionLogs)
    marker = tmp_path / "must-not-exist"
    expression = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    with pytest.raises((ValueError, SyntaxError)):
        replay.parse_bid(expression)
    assert not marker.exists()


def test_session_end_receives_the_final_tournament_row(tmp_path):
    """Pass the reconstructed terminal result to the session-end logger."""
    path = tmp_path / "session.xlsx"
    workbook(path)
    replay = SessionLogs(*agents(), str(path), [RecordingLogger(str(tmp_path))])
    result = replay.start({"TournamentResults": {}})
    assert result["Recorded"]["Result"] == "Failed"


@pytest.mark.parametrize("result", ["Error", "TimedOut", "Failed"])
@pytest.mark.parametrize("with_logger", [False, True])
def test_reprocessing_preserves_known_terminal_outcomes(tmp_path, result, with_logger):
    """Retain recorded terminal outcomes with or without additional loggers."""
    path = tmp_path / "session.xlsx"
    workbook(path)
    loggers = [RecordingLogger(str(tmp_path))] if with_logger else []
    replay = SessionLogs(*agents(), str(path), loggers)
    original = {"Result": result, "Round": 7, "Time": .37, "Who": "B", "NumOffer": 1,
                "AgentAUtility": .1, "AgentBUtility": 0., "ProductScore": 0.,
                "SocialWelfare": .1, "BidContent": None}
    output = replay.start({"TournamentResults": copy.deepcopy(original)})
    assert output["TournamentResults"] == original


def test_failure_is_reconstructed_even_without_loggers(tmp_path):
    """Reconstruct an incomplete session result when no loggers are configured."""
    path = tmp_path / "session.xlsx"
    workbook(path)
    replay = SessionLogs(*agents(), str(path), [])
    output = replay.start({"TournamentResults": {}})
    assert output["TournamentResults"]["Result"] == "Failed"
    assert output["TournamentResults"]["NumOffer"] == 1


def test_estimated_distances_use_the_same_model_as_their_bid_space(tmp_path):
    """Compute each estimated distance with its corresponding opponent model."""
    pref_a = preference({"a": 1., "b": .2})
    pref_b = preference({"a": .3, "b": 1.})
    model_a = SimpleNamespace(name="Model", preference=preference({"a": .1, "b": 1.}))
    model_b = SimpleNamespace(name="Model", preference=preference({"a": 1., "b": .8}))
    session = SimpleNamespace(agentA=SimpleNamespace(preference=pref_a, estimators=[model_a]),
                              agentB=SimpleNamespace(preference=pref_b, estimators=[model_b]))
    offer = Bid({"issue": "a"})
    output = EstimatedBidSpaceLogger(str(tmp_path)).on_offer("A", offer, .1, session)["Model"]
    space_a = BidSpace(pref_a, model_a.preference)
    space_b = BidSpace(model_b.preference, pref_b)
    assert output["EstimatedNashDistanceA"] == pytest.approx(space_a.nash_distance(offer))
    assert output["EstimatedNashDistanceB"] == pytest.approx(space_b.nash_distance(offer))
    assert output["EstimatedKalaiDistanceA"] == pytest.approx(space_a.kalai_distance(offer))
    assert output["EstimatedKalaiDistanceB"] == pytest.approx(space_b.kalai_distance(offer))


def test_move_accuracy_is_written_and_undefined_classes_stay_nan(tmp_path, monkeypatch):
    """Export move accuracy while keeping unsupported class statistics undefined."""
    module = importlib.import_module("nenv.logger.EstimatedMoveLogger")
    monkeypatch.setattr(module, "draw_heatmap", lambda *args, **kwargs: None)
    (tmp_path / "sessions").mkdir()
    path = tmp_path / "sessions/A_B_Domain0.xlsx"
    session_log = ExcelLog(["Session", "Model"])
    session_log.append({"Session": {"Move": "Concession"},
                        "Model": {"EstimatedMoveA": "Concession", "EstimatedMoveB": "Concession"}})
    session_log.save(str(path))
    tournament = ExcelLog(["TournamentResults"])
    tournament.append({"TournamentResults": {"AgentA": "A", "AgentB": "B", "DomainName": "0",
                                               "FilePath": str(path)}})
    logger = EstimatedMoveLogger(str(tmp_path))
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        logger.on_tournament_end(tournament, ["A", "B"], ["0"], ["Model"])
    exported = pd.read_excel(tmp_path / "opponent model/estimator_move_performance.xlsx")
    assert exported.loc[0, "Accuracy"] == 1.
    assert np.isnan(exported.loc[0, "F1"])


def test_empty_move_classes_remain_undefined_without_runtime_warnings(tmp_path):
    """Return undefined empty-class metrics without emitting runtime warnings."""
    logger = EstimatedMoveLogger(str(tmp_path))
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        _, _, _, recall, precision, f1 = logger.calculate([np.zeros((6, 6), dtype=int)], ["Model"])
    assert all(np.isnan(value) for values in (recall, precision, f1) for value in values[0].values())


def test_live_session_records_each_acceptance_once(tmp_path):
    """Record exactly one acceptance in both action history and session rows."""
    manager = SessionManager(BoulwareAgent, ConcederAgent, "0", None, 20, [], [])
    result = manager.run(str(tmp_path / "session.xlsx"))
    history = manager.session.action_history
    rows = manager.session.session_log.log_rows["Session"]
    assert result["TournamentResults"]["Result"] == "Acceptance"
    assert sum(isinstance(action, Accept) for action in history) == 1
    assert len(history) == len(rows)
    assert result["TournamentResults"]["NumOffer"] == len(history) - 1
