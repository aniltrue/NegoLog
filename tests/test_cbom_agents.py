"""Exercise CBOM adapters through real sessions, logs, and subprocess lifecycles."""

import importlib
import json
from pathlib import Path
import shutil
import sys
import time

import pytest

import nenv
from agents import BoulwareAgent, CBOMAgent, CBOMJavaAgent, ConcederAgent
from agents.CBOM.java_bridge import JavaBridge
from agents.CBOM.common import profile_snapshot
from nenv.OpponentModel import ClassicFrequencyOpponentModel
from nenv.logger import EstimatorMetricLogger
from nenv.logger import AbstractLogger
from nenv.utils.ExcelLog import ExcelLog


JAVA_READY = (shutil.which("java") is not None
              and (Path(__file__).resolve().parents[1] / "agents/CBOM/java/build/cbom.jar").is_file())
java_case = pytest.mark.skipif(not JAVA_READY, reason="Build CBOM Java with a JDK first")
ENGINES = [CBOMAgent, pytest.param(CBOMJavaAgent, marks=java_case)]


def profile(values=None, reservation=0.):
    return nenv.EditablePreference({"choice": 1.},
                                   {"choice": values or {"best": 1., "middle": .6, "bad": 0.}},
                                   reservation)


def manager_with_profiles(monkeypatch, classes, profiles, directory, rounds=30, loggers=None):
    stored = []
    for index, preference in enumerate(profiles):
        path = directory / f"profile-{index}.json"
        path.write_text(json.dumps(profile_snapshot(preference).to_dict()), encoding="utf-8")
        stored.append(nenv.Preference(str(path)))
    module = importlib.import_module("nenv.SessionManager")
    monkeypatch.setattr(module, "domain_loader", lambda name: stored)
    return nenv.SessionManager(*classes, "fixture", None, rounds,
                               [ClassicFrequencyOpponentModel], loggers or [])


def assert_closed(agent):
    bridge = getattr(agent, "_bridge", None)
    if bridge is not None:
        assert bridge.process.poll() is not None
        assert not bridge._reader.is_alive()
        if bridge._writer is not None:
            assert not bridge._writer.is_alive()


@pytest.mark.parametrize("agent_class", ENGINES)
@pytest.mark.parametrize("opponent", [BoulwareAgent, ConcederAgent])
@pytest.mark.parametrize("first", [True, False])
def test_cbom_runs_with_public_agents_in_both_roles(tmp_path, agent_class, opponent, first):
    classes = (agent_class, opponent) if first else (opponent, agent_class)
    manager = nenv.SessionManager(*classes, "0", None, 30, [], [])
    result = manager.run(str(tmp_path / "session.xlsx"))["TournamentResults"]
    assert result["Result"] in {"Acceptance", "Failed"}
    history = manager.session.action_history
    assert history
    for index, action in enumerate(history):
        if isinstance(action, nenv.Accept):
            assert index > 0 and action.bid == history[index - 1].bid
        elif isinstance(action, nenv.EndNegotiation):
            assert action.bid is None and index == len(history) - 1
        else:
            manager.prefA.get_utility(action.bid)
            manager.prefB.get_utility(action.bid)
    for agent in (manager.agentA, manager.agentB):
        assert_closed(agent)


@java_case
@pytest.mark.parametrize("classes", [(CBOMAgent, CBOMJavaAgent),
                                     (CBOMJavaAgent, CBOMAgent),
                                     (CBOMJavaAgent, CBOMJavaAgent)])
def test_mixed_and_java_only_sessions_finish_and_reap_both_children(tmp_path, classes):
    manager = nenv.SessionManager(*classes, "0", None, 40, [], [])
    result = manager.run(str(tmp_path / "mixed.xlsx"))["TournamentResults"]
    assert result["Result"] in {"Acceptance", "Failed"}
    for agent in (manager.agentA, manager.agentB):
        assert_closed(agent)


@pytest.mark.parametrize("agent_class", ENGINES)
@pytest.mark.parametrize("first", [True, False])
def test_unattainable_reservation_ends_without_a_fake_offer_or_error(
        tmp_path, monkeypatch, agent_class, first):
    own = profile({"best": .8, "middle": .6, "bad": 0.}, reservation=.9)
    other = profile(reservation=.1)
    classes = (agent_class, BoulwareAgent) if first else (BoulwareAgent, agent_class)
    prefs = (own, other) if first else (other, own)
    manager = manager_with_profiles(monkeypatch, classes, prefs, tmp_path,
                                    loggers=[EstimatorMetricLogger(str(tmp_path))])
    path = tmp_path / "ended.xlsx"
    result = manager.run(str(path))["TournamentResults"]
    assert result["Result"] == "Failed"
    assert result["Who"] == ("A" if first else "B")
    assert result["EndReason"] == "no outcome meets reservation utility"
    assert result["NumOffer"] == (0 if first else 1)
    assert result["AgentAUtility"] == prefs[0].reservation_value
    assert result["AgentBUtility"] == prefs[1].reservation_value
    assert isinstance(manager.session.action_history[-1], nenv.EndNegotiation)
    rows = manager.session.session_log.log_rows["Session"]
    assert rows[-1]["Action"] == "End" and rows[-1]["BidContent"] is None
    assert len(rows) == result["NumOffer"] + 1
    assert_closed(manager.agentA)
    assert_closed(manager.agentB)
    # A bidless End row must not be parsed or sent to an opponent estimator.
    replay = nenv.SessionLogs(manager.agentA, manager.agentB, str(path), [])
    replayed = replay.start({"TournamentResults": {}})["TournamentResults"]
    for field in ("Result", "Who", "NumOffer", "EndReason", "AgentAUtility", "AgentBUtility"):
        assert replayed[field] == result[field]


@pytest.mark.parametrize("agent_class", ENGINES)
def test_candidate_exhaustion_is_valid_no_agreement(tmp_path, monkeypatch, agent_class):
    own = profile({"best": 1., "bad": 0.}, reservation=.5)
    other = profile({"best": 0., "bad": 1.})
    manager = manager_with_profiles(monkeypatch, (agent_class, BoulwareAgent), (own, other), tmp_path)
    result = manager.run(str(tmp_path / "exhausted.xlsx"))["TournamentResults"]
    assert result["Result"] == "Failed"
    assert result["EndReason"] == "candidate pool exhausted"
    assert_closed(manager.agentA)


@pytest.mark.parametrize("agent_class", ENGINES)
@pytest.mark.parametrize("received", [False, True])
def test_deadline_can_accept_a_current_offer_but_never_emits_a_new_one(agent_class, received):
    agent = agent_class(profile(), 30, [])
    agent.initiate("Opponent")
    try:
        if received:
            agent.receive_bid(nenv.Bid({"choice": "best"}), .9)
        action = agent.act(1.)
        assert isinstance(action, nenv.Accept if received else nenv.EndNegotiation)
    finally:
        agent.terminate(False, "Opponent", 1.)
    assert_closed(agent)


@pytest.mark.parametrize("agent_class", ENGINES)
def test_near_reservation_candidate_does_not_hide_a_valid_offer(agent_class):
    pref = profile({"best": .9, "near": .8 - 5e-13, "feasible": .85, "bad": 0.}, .8)
    agent = agent_class(pref, 30, [])
    agent.cbom_options = {"epsilon": 0., "mode": "exact"}
    agent.initiate("Opponent")
    try:
        assert agent.act(0.).bid["choice"] == "best"
        agent.receive_bid(nenv.Bid({"choice": "bad"}), .8)
        action = agent.act(.8)
        assert isinstance(action, nenv.Offer) and action.bid["choice"] == "feasible"
    finally:
        agent.terminate(False, "Opponent", 1.)
    assert_closed(agent)


@pytest.mark.parametrize("agent_class", ENGINES)
def test_counteroffer_expires_the_previous_received_offer(agent_class):
    pref = profile({"a": 1., "b": .8, "c": .5, "d": 0.})
    agent = agent_class(pref, 30, [])
    agent.initiate("Opponent")
    try:
        agent.receive_bid(nenv.Bid({"choice": "b"}), 0.)
        assert agent.act(0.).bid["choice"] == "a"
        assert isinstance(agent.act(.8), nenv.Offer)
        agent.receive_bid(nenv.Bid({"choice": "b"}), .9)
        assert isinstance(agent.act(.9), nenv.Accept)
    finally:
        agent.terminate(False, "Opponent", 1.)
    assert_closed(agent)


@pytest.mark.parametrize("agent_class", ENGINES)
def test_both_adapters_honor_the_same_history_size_option(agent_class):
    agent = agent_class(profile(), 30, [])
    agent.cbom_options = {"history_size": 1}
    agent.initiate("Opponent")
    try:
        for step, value in enumerate(["best", "middle", "bad"]):
            agent.receive_bid(nenv.Bid({"choice": value}), step / 10)
        comparisons = (agent.core.model.comparisons if isinstance(agent, CBOMAgent)
                       else agent._bridge.request({"op": "inspect"})["result"]["comparisons"])
        assert comparisons == 2  # Only the preceding offer enters each update.
        assert agent.cbom_options == {"history_size": 1}
    finally:
        agent.terminate(False, "Opponent", 1.)
    assert_closed(agent)


@java_case
@pytest.mark.parametrize("callback,role", [("initiate", "A"), ("act", "A"), ("receive_offer", "B")])
def test_java_child_is_reaped_after_real_session_callback_failure(tmp_path, callback, role):
    original = getattr(CBOMJavaAgent, callback)

    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise ValueError("intentional callback failure after Java initialization")

    broken = type("BrokenJava", (CBOMJavaAgent,), {callback: fail})
    classes = (broken, CBOMAgent) if role == "A" else (CBOMAgent, broken)
    manager = nenv.SessionManager(*classes, "0", None, 30, [], [])
    result = manager.run(str(tmp_path / "failure.xlsx"))["TournamentResults"]
    assert result["Result"] == "Error" and result["Who"] == role
    assert_closed(manager.agentA)
    assert_closed(manager.agentB)


@java_case
def test_failed_java_initialization_request_reaps_the_child(tmp_path):
    class InvalidJava(CBOMJavaAgent):
        cbom_options = {"epsilon": 2.}

    manager = nenv.SessionManager(InvalidJava, CBOMAgent, "0", None, 30, [], [])
    result = manager.run(str(tmp_path / "invalid-init.xlsx"))["TournamentResults"]
    assert result["Result"] == "Error" and result["Who"] == "A"
    assert_closed(manager.agentA)


@java_case
def test_session_callback_timeout_also_reaps_the_jvm(tmp_path, monkeypatch):
    class HangingJava(CBOMJavaAgent):
        def act(self, t):
            while True:
                pass

    class ShortActSession(nenv.Session):
        def _run_process_manager(self, agent_no, process_name, call_events=True, **kwargs):
            self.time_out = .03 if process_name == "Act" else 10.
            return super()._run_process_manager(agent_no, process_name, call_events, **kwargs)

    module = importlib.import_module("nenv.SessionManager")
    monkeypatch.setattr(module, "Session", ShortActSession)
    manager = nenv.SessionManager(HangingJava, CBOMAgent, "0", None, 30, [], [])
    result = manager.run(str(tmp_path / "timeout.xlsx"))["TournamentResults"]
    assert result["Result"] == "TimedOut" and result["Who"] == "A"
    assert_closed(manager.agentA)


@java_case
@pytest.mark.parametrize("failure", ["logger", "workbook"])
def test_unexpected_host_failure_preserves_exception_and_reaps_java(tmp_path, monkeypatch, failure):
    original = RuntimeError("intentional host failure")

    class BrokenLogger(AbstractLogger):
        def on_offer(self, *args):
            raise original

    def broken_save(*args, **kwargs):
        raise original

    loggers = [BrokenLogger(str(tmp_path))] if failure == "logger" else []
    if failure == "workbook":
        monkeypatch.setattr(ExcelLog, "save", broken_save)
    manager = nenv.SessionManager(CBOMJavaAgent, CBOMJavaAgent, "0", None, 30, [], loggers)
    with pytest.raises(RuntimeError) as raised:
        manager.run(str(tmp_path / "host-failure.xlsx"))
    assert raised.value is original
    assert_closed(manager.agentA)
    assert_closed(manager.agentB)


@pytest.mark.parametrize("reply", ["not-json", "[]", '{"ok":1}', '{"ok":false,"error":"bad input"}'])
def test_bridge_rejects_bad_replies_and_reaps_process(reply):
    script = "import sys,time;sys.stdin.readline();print(" + repr(reply) + ",flush=True);time.sleep(10)"
    bridge = JavaBridge([sys.executable, "-u", "-c", script], 2.)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        bridge.request({"op": "init"})
    assert bridge.process.poll() is not None
    assert not bridge._reader.is_alive()


@pytest.mark.parametrize("payload", [{"op": "act"}, {"op": "init", "large": "x" * 200000}])
def test_bridge_timeout_covers_a_peer_that_stops_reading_or_responding(payload):
    bridge = JavaBridge([sys.executable, "-u", "-c", "import time;time.sleep(10)"], .05)
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        bridge.request(payload)
    assert time.monotonic() - start < 3.
    assert bridge.process.poll() is not None
    assert not bridge._reader.is_alive() and not bridge._writer.is_alive()


def test_missing_java_build_does_not_affect_python_agents(tmp_path):
    agent = CBOMJavaAgent(profile(), 30, [])
    agent.java_jar = tmp_path / "missing.jar"
    with pytest.raises(FileNotFoundError, match="build.py"):
        agent.initiate("Opponent")
    agent.terminate(False, "Opponent", 0.)
    native = CBOMAgent(profile(), 30, [])
    native.initiate("Opponent")
    assert isinstance(native.act(0.), nenv.Offer)
