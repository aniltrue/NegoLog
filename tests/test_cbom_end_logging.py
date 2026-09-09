"""An explicit CBOM end is not a movement or a missing-bid replay event."""

import copy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import nenv
from agents import BoulwareAgent, CBOMAgent
from nenv.logger import MoveAnalyzeLogger
from nenv.logger.DomainGraphsLogger import DomainGraphsLogger
from nenv.utils.ExcelLog import ExcelLog


@pytest.mark.parametrize("before_first_offer", [True, False])
def test_cbom_end_with_move_logger_runs_and_replays(tmp_path, monkeypatch, before_first_offer):
    profiles = []
    for side in range(2):
        profile = {
            "issueWeights": {"x": 1.},
            "issues": {"x": ({"a": .8 if before_first_offer else 1., "b": .8, "c": .6, "d": 0.}
                             if side == 0 else {"a": 0., "b": .2, "c": .4, "d": 1.})},
            "reservationValue": (.9 if before_first_offer else .5) if side == 0 else .1,
        }
        path = tmp_path / f"profile-{side}.json"
        path.write_text(json.dumps(profile))
        profiles.append(nenv.Preference(str(path)))
    monkeypatch.setattr(importlib.import_module("nenv.SessionManager"), "domain_loader", lambda _: profiles)
    logger = MoveAnalyzeLogger(str(tmp_path))
    manager = nenv.SessionManager(CBOMAgent, BoulwareAgent, "fixture", None, 30, [], [logger])
    workbook = tmp_path / "session.xlsx"
    outcome = manager.run(str(workbook))
    assert outcome["TournamentResults"]["Result"] == "Failed"
    assert manager.session.last_row["Action"] == "End"
    if before_first_offer:
        assert outcome["TournamentResults"]["NumOffer"] == 0
        assert outcome["MoveAnalyze"] == {}
    else:
        assert outcome["TournamentResults"]["NumOffer"] > 0
    replay = nenv.SessionLogs(CBOMAgent(profiles[0], 30, []), BoulwareAgent(profiles[1], 30, []),
                              str(workbook), [MoveAnalyzeLogger(str(tmp_path))])
    reconstructed = replay.start(copy.deepcopy(outcome))
    assert reconstructed["MoveAnalyze"] == outcome["MoveAnalyze"]
    for key in ("Result", "NumOffer", "EndReason", "AgentAUtility", "AgentBUtility"):
        assert reconstructed["TournamentResults"][key] == outcome["TournamentResults"][key]


def test_terminal_rows_do_not_change_move_statistics(tmp_path):
    rows = [{"Who": "A", "Action": "Offer", "Move": "Concession"},
            {"Who": "B", "Action": "Offer", "Move": "Silent"}]
    session = SimpleNamespace(session_log=SimpleNamespace(log_rows={"Session": rows}))
    logger = MoveAnalyzeLogger(str(tmp_path))
    before = logger.analyze_moves("A", session)
    rows.extend([{"Who": "A", "Action": "End", "Move": "Selfish"},
                 {"Who": "A", "Action": "Accept"}])
    assert logger.analyze_moves("A", session) == before


def test_domain_graphs_use_raw_domain_id_and_separate_output_directories(tmp_path, monkeypatch):
    log = ExcelLog(["TournamentResults"])
    for domain, utility in [("0", .25), ("fixture", .75)]:
        log.append({"TournamentResults": {"DomainName": domain, "AgentAUtility": utility}})
    received = []
    logger = DomainGraphsLogger(str(tmp_path))
    monkeypatch.setattr(logger, "draw_opponent_based",
                        lambda rows, names, directory: received.append((rows, directory)))
    logger.on_tournament_end(log, ["CBOM", "Boulware"], ["0", "fixture"], [])
    assert [rows["AgentAUtility"].tolist() for rows, _ in received] == [[.25], [.75]]
    assert [rows["DomainName"].tolist() for rows, _ in received] == [["0"], ["fixture"]]
    assert [tmp_path / "domains" / name for name in ["Domain0", "Domainfixture"]] == [
        Path(directory) for _, directory in received]
