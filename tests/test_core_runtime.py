"""Regression checks for real session errors and persisted tournament output."""
import importlib
import math
from pathlib import Path

import pandas as pd
import pytest

from agents import BoulwareAgent, ConcederAgent
from nenv import Bid, Issue, SessionManager, Tournament
from nenv.OpponentModel import BayesianOpponentModel
from nenv.logger import AbstractLogger, EstimatorMetricLogger
from nenv.utils.ProcessManager import ProcessManager


def test_equal_bid_contents_have_equal_hashes_in_any_issue_order():
    issue = Issue("color", ["red", "blue"])
    left = Bid({issue: "red", "size": "large"}, .8)
    right = Bid({"size": "large", "color": "red"}, .2)
    assert left == right
    assert hash(left) == hash(right)
    assert len({left, right}) == 1
    assert {left: "observed"}[right] == "observed"
    # Different or incomplete domains are unequal, without a KeyError.
    partial = Bid({"color": "red"})
    assert not (left == partial or partial == left)
    assert not (left == {} or left == {"color": "red"})
    assert left == .8  # Preserve the legacy utility-comparison convenience.


@pytest.mark.parametrize("arguments", [None, [], {}, [1], {"value": 1}])
def test_process_errors_are_recorded_and_do_not_leak_to_next_call(arguments):
    manager = ProcessManager()
    error = ValueError("callback failed")

    def fail(*args, **kwargs):
        raise error

    assert manager.run(fail, 2., arguments) is None
    assert manager.has_exception and manager.exception is error
    assert not manager.time_outed
    assert manager.run(lambda: 42, 2.) == 42
    assert not manager.has_exception and manager.exception is None


def test_python_callback_timeout_still_uses_timeout_status():
    def busy():
        while True:
            pass

    manager = ProcessManager()
    manager.run(busy, .02)
    assert manager.time_outed and not manager.has_exception
    assert not manager.thread.is_alive()


@pytest.mark.parametrize("callback,role", [("initiate", "A"), ("act", "A"), ("receive_offer", "B")])
def test_callback_failure_ends_real_session_with_an_error_record(tmp_path, callback, role):
    def fail(self, *args, **kwargs):
        raise ValueError("intentional callback failure")

    Broken = type("BrokenAgent", (BoulwareAgent,), {callback: fail})
    agents = (Broken, ConcederAgent) if role == "A" else (BoulwareAgent, Broken)
    manager = SessionManager(*agents, "0", None, 8, [], [])
    result = manager.run(str(tmp_path / "session.xlsx"))["TournamentResults"]
    assert result["Result"] == "Error" and result["Who"] == role
    assert 0 <= result["ElapsedTime"] < 10
    assert math.isfinite(result["AgentAUtility"])
    assert (tmp_path / "session.xlsx").is_file()


def test_class_input_order_is_stable_and_single_agent_empty_tournament_is_rejected(tmp_path):
    kwargs = dict(domains=["0"], logger_classes=[], estimator_classes=[],
                  deadline_time=None, deadline_round=8, result_dir=str(tmp_path / "results"))
    tournament = Tournament([ConcederAgent, BoulwareAgent, ConcederAgent], **kwargs)
    assert tournament.agent_classes == [ConcederAgent, BoulwareAgent]
    expected = sorted([ConcederAgent, BoulwareAgent], key=lambda cls: (cls.__module__, cls.__qualname__))
    assert Tournament({ConcederAgent, BoulwareAgent}, **kwargs).agent_classes == expected
    with pytest.raises(ValueError, match="two different agents"):
        Tournament([BoulwareAgent, BoulwareAgent], **kwargs)
    assert Tournament([BoulwareAgent], self_negotiation=True, **kwargs).generate_combinations()


def test_repeated_sessions_keep_separate_workbooks_and_estimator_observations(tmp_path, monkeypatch):
    module = importlib.import_module("nenv.Tournament")
    monkeypatch.setattr(module, "open_folder", lambda path: None)

    class ReadMetrics(EstimatorMetricLogger):
        def on_tournament_end(self, logs, agent_names, domains, estimator_names):
            self.series = self.get_estimator_results(logs, estimator_names)[0]

    output = tmp_path / "run"
    tournament = Tournament([BoulwareAgent, ConcederAgent], ["0"], [ReadMetrics],
                            [BayesianOpponentModel], None, 8, repeat=2,
                            result_dir=str(output), seed=42)
    tournament.run()
    results = pd.read_excel(output / "results.xlsx", sheet_name="TournamentResults")
    assert len(results) == results["FilePath"].nunique() == 4
    assert len(list((output / "sessions").glob("*.xlsx"))) == 4
    assert sum("_repeat2" in path for path in results["FilePath"]) == 2
    offers = 0
    for path in results["FilePath"]:
        assert Path(path).is_file()
        session = pd.read_excel(path, sheet_name="Session")
        offers += int((session["Action"] == "Offer").sum())
    series = next(iter(tournament.loggers[0].series.values()))
    assert sum(len(round_values) for round_values in series) == 2 * offers


def test_recorded_session_filename_survives_copied_results_and_legacy_names(tmp_path):
    logger = AbstractLogger(str(tmp_path))
    (tmp_path / "sessions").mkdir()
    local = tmp_path / "sessions/a_b_Domaincustom_repeat2.xlsx"
    local.touch()
    row = {"AgentA": "a", "AgentB": "b", "DomainName": "custom",
           "FilePath": r"C:\old\results\sessions\a_b_Domaincustom_repeat2.xlsx"}
    assert Path(logger.get_session_path(row)) == local
    row.pop("FilePath")
    assert logger.get_session_path(row).endswith("a_b_Domaincustom.xlsx")
    row["DomainName"] = 2.
    assert logger.get_session_path(row).endswith("a_b_Domain2.xlsx")


def test_repeat_suffix_cannot_collide_with_another_domain_name(tmp_path, monkeypatch):
    module = importlib.import_module("nenv.Tournament")
    manager = importlib.import_module("nenv.SessionManager")
    load = manager.domain_loader
    read_excel = pd.read_excel

    def catalog_with_synthetic_domain(path, *args, **kwargs):
        result = read_excel(path, *args, **kwargs)
        if Path(path) == Path("domains/domains.xlsx"):
            extra = result.loc[result["DomainName"].astype(str) == "0"].copy()
            extra["DomainName"] = "0_repeat2"
            return pd.concat([result, extra], ignore_index=True)
        return result

    monkeypatch.setattr(module.pd, "read_excel", catalog_with_synthetic_domain)
    monkeypatch.setattr(module, "open_folder", lambda path: None)
    monkeypatch.setattr(manager, "domain_loader", lambda name: load("0"))
    output = tmp_path / "run"
    Tournament([BoulwareAgent, ConcederAgent], ["0", "0_repeat2"], [], [], None, 2,
               repeat=2, result_dir=str(output), seed=42).run()
    results = pd.read_excel(output / "results.xlsx", sheet_name="TournamentResults")
    assert len(results) == results["FilePath"].nunique() == 8
    assert len(list((output / "sessions").glob("*.xlsx"))) == 8


def test_tournament_with_initialization_errors_finishes_without_fake_curves(tmp_path, monkeypatch):
    module = importlib.import_module("nenv.Tournament")
    monkeypatch.setattr(module, "open_folder", lambda path: None)

    class Broken(BoulwareAgent):
        def initiate(self, opponent_name):
            raise ValueError("initialization failed")

    output = tmp_path / "run"
    tournament = Tournament([Broken, ConcederAgent], ["0"], [EstimatorMetricLogger],
                            [BayesianOpponentModel], None, 2, result_dir=str(output))
    tournament.run()
    results = pd.read_excel(output / "results.xlsx", sheet_name="TournamentResults")
    assert results["Result"].tolist() == ["Error", "Error"]
    assert not tournament.tournament_process.is_active
    assert not list(output.rglob("*.png"))
    assert EstimatorMetricLogger.get_median_round({"model": [[], []]}) == 0
    mean, std = EstimatorMetricLogger.get_mean_std({"model": [[], [.5]]})
    assert math.isnan(mean["model"][0]) and math.isnan(std["model"][0])
    assert mean["model"][1] == .5
