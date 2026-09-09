"""Validate shared configuration and preserve results on preflight failures."""

import copy
import importlib
from pathlib import Path
import runpy
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

from agents import BoulwareAgent, ConcederAgent
from nenv import Tournament
from nenv.OpponentModel import BayesianOpponentModel
from nenv.utils.DynamicImport import load_agent_class, load_estimator_class, load_logger_class
from nenv.utils.ExcelLog import ExcelLog
from nenv.utils.TournamentConfig import load_tournament_config


@pytest.fixture
def configuration():
    """Provide valid settings with registered and full component names."""
    return {"agents": ["BoulwareAgent", "agents.ConcederAgent"], "domains": ["0"],
            "deadline_round": 1, "estimators": ["BayesianOpponentModel"],
            "loggers": [], "drawing_format": "matplotlib-SVG"}


def tournament(tmp_path, **overrides):
    """Construct a minimal tournament with isolated result storage."""
    arguments = {"agent_classes": [BoulwareAgent, ConcederAgent], "domains": ["0"],
                 "logger_classes": [], "estimator_classes": [], "deadline_time": None,
                 "deadline_round": 1, "result_dir": str(tmp_path / "results")}
    arguments.update(overrides)
    return Tournament(**arguments)


def test_mapping_configuration_is_deep_copied_and_classes_resolve(configuration):
    """Resolve component names without mutating the supplied configuration."""
    original = copy.deepcopy(configuration)
    arguments, drawing = load_tournament_config(configuration)
    assert arguments["agent_classes"] == [BoulwareAgent, ConcederAgent]
    assert arguments["estimator_classes"] == [BayesianOpponentModel]
    assert arguments["deadline_time"] is None
    assert drawing == "matplotlib-SVG"
    arguments["domains"].append("other")
    assert configuration == original


def test_yaml_path_and_mapping_produce_the_same_configuration(tmp_path, configuration):
    """Load equivalent settings from YAML files and in-memory mappings."""
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    assert load_tournament_config(path) == load_tournament_config(configuration)


@pytest.mark.parametrize("change", [{"unknown_setting": True}, {"agents": []}, {"agents": "BoulwareAgent"},
                                    {"domains": []}, {"domains": "0"}, {"loggers": "BidSpaceLogger"},
                                    {"estimators": {}}, {"drawing_format": "unknown"}])
def test_invalid_configuration_fields_are_rejected(configuration, change):
    """Reject unsupported fields and invalid collection settings."""
    configuration.update(change)
    with pytest.raises(ValueError):
        load_tournament_config(configuration)


@pytest.mark.parametrize("source", [None, [], 1, True, ""])
def test_nonmapping_yaml_is_rejected(tmp_path, source):
    """Reject YAML documents that do not contain a configuration mapping."""
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.safe_dump(source), encoding="utf-8")
    with pytest.raises(ValueError):
        load_tournament_config(path)


@pytest.mark.parametrize("loader,path", [(load_agent_class, "builtins.str"),
                                         (load_agent_class, "nenv.Agent.AbstractAgent"),
                                         (load_agent_class, "builtins.len"),
                                         (load_estimator_class, "nenv.OpponentModel.AbstractOpponentModel"),
                                         (load_estimator_class, "builtins.int"),
                                         (load_logger_class, "agents.BoulwareAgent")])
def test_component_paths_must_resolve_to_the_correct_concrete_class(loader, path):
    """Reject abstract classes and components of the wrong framework type."""
    with pytest.raises(TypeError):
        loader(path)


@pytest.mark.parametrize("loader", [load_agent_class, load_estimator_class, load_logger_class])
@pytest.mark.parametrize("path", [None, "", " ", 7])
def test_component_paths_must_be_nonempty_strings(loader, path):
    """Require a nonempty string for each component import path."""
    with pytest.raises(ValueError):
        loader(path)


@pytest.mark.parametrize("overrides", [{"deadline_round": None}, {"deadline_round": 0},
    {"deadline_round": True}, {"deadline_round": 1.5}, {"deadline_time": 0},
    {"deadline_time": float("nan")}, {"deadline_time": float("inf")}, {"deadline_time": True},
    {"deadline_time": "1"}, {"seed": -1}, {"seed": 2**32}, {"seed": 1.5}, {"seed": True},
    {"repeat": True}, {"repeat": 1.5}, {"shuffle": "false"}, {"self_negotiation": 1},
    {"domains": [True]}, {"domains": ["../0"]}])
def test_invalid_numeric_and_structural_settings_fail_before_writes(tmp_path, overrides):
    """Reject invalid settings before modifying existing result files."""
    output = tmp_path / "results"
    output.mkdir()
    marker = output / "previous.txt"
    marker.write_text("preserve")
    with pytest.raises(ValueError):
        tournament(tmp_path, **overrides)
    assert marker.read_text() == "preserve"


@pytest.mark.parametrize("repeat", [0, -3])
def test_nonpositive_repeat_retains_documented_legacy_fallback(tmp_path, repeat):
    """Retain the documented warning and fallback for nonpositive repeats."""
    with pytest.warns(UserWarning, match="repeat is set to 1"):
        instance = tournament(tmp_path, repeat=repeat)
    assert instance.repeat == 1


@pytest.mark.parametrize("relative", [".", "..", "nenv", "nenv/new-output", "domains", ".git",
                                      "tournament_configurations", "tests"])
def test_destructive_project_result_directories_are_rejected(tmp_path, relative):
    """Protect project sources and inputs from result-directory replacement."""
    project = Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError):
        tournament(tmp_path, result_dir=str(project / relative))


def test_result_directory_rejects_file_and_symlink_without_writes(tmp_path):
    """Reject file and symlink outputs while preserving their targets."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("preserve")
    with pytest.raises(ValueError):
        tournament(tmp_path, result_dir=file_path)
    target = tmp_path / "old-results"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Creating directory symlinks requires platform privileges.")
    with pytest.raises(ValueError):
        tournament(tmp_path, result_dir=link)
    assert file_path.read_text() == "preserve"
    assert target.is_dir()


@pytest.mark.parametrize("field", ["agent_classes", "estimator_classes"])
def test_direct_constructor_rejects_invalid_component_classes(tmp_path, field):
    """Apply component type validation to direct tournament construction."""
    invalid = [BoulwareAgent, object] if field == "agent_classes" else [object]
    with pytest.raises((TypeError, ValueError)):
        tournament(tmp_path, **{field: invalid})


def test_missing_domain_does_not_replace_existing_results(tmp_path, monkeypatch):
    """Preserve prior results when selected domain profiles cannot be loaded."""
    output = tmp_path / "results"
    output.mkdir()
    marker = output / "previous.txt"
    marker.write_text("preserve")
    instance = tournament(tmp_path, domains=["domain-that-does-not-exist"])
    module = importlib.import_module("nenv.Tournament")
    monkeypatch.setattr(module.pd, "read_excel", lambda *args, **kwargs:
                        pd.DataFrame({"DomainName": ["domain-that-does-not-exist"]}))
    with pytest.raises(FileNotFoundError):
        instance.run()
    assert marker.read_text() == "preserve"
    assert instance.failure
    assert not instance.tournament_process.is_active
    assert not instance.tournament_process.is_completed


def test_prestart_cancellation_closes_pending_monitor_and_preserves_results(tmp_path, monkeypatch):
    """Honor pending cancellation without starting work or replacing results."""
    instance = tournament(tmp_path)
    output = tmp_path / "results"
    output.mkdir()
    marker = output / "previous.txt"
    marker.write_text("preserve")
    instance.tournament_process.current_session = "Pending"
    instance.tournament_process.is_active = True
    instance.killed = True
    monkeypatch.setattr(instance, "_run", lambda: pytest.fail("Cancelled tournament must not start."))
    instance.run()
    assert instance.cancelled and instance.failure is None
    assert not instance.tournament_process.is_active
    assert not instance.tournament_process.is_completed
    assert instance.tournament_process.current_session == "Cancelled"
    assert marker.read_text() == "preserve"


@pytest.mark.parametrize("message", ["intentional analysis failure", ""])
def test_run_failure_saves_partial_results_and_closes_monitor(tmp_path, monkeypatch, message):
    """Preserve completed results and report a closed error state after failure."""
    instance = tournament(tmp_path)
    output = tmp_path / "results"
    output.mkdir()

    def fail_after_result():
        """Simulate a tournament failure after recording one completed result."""
        instance.tournament_process.initiate(2)
        instance._tournament_logs = ExcelLog(["TournamentResults"])
        instance._tournament_logs.append({"TournamentResults": {"Result": "Acceptance", "Round": 2}})
        raise RuntimeError(message)

    monkeypatch.setattr(instance, "_run", fail_after_result)
    with pytest.raises(RuntimeError, match=message or "^$"):
        instance.run()
    assert instance.failure == (message or "RuntimeError")
    assert not instance.cancelled
    assert not instance.tournament_process.is_active
    assert not instance.tournament_process.is_completed
    assert instance.tournament_process.current_session == "Error"
    assert ExcelLog(file_path=str(output / "results.xlsx"))[0, "TournamentResults"]["Round"] == 2


def test_domain_metadata_is_selected_by_name_and_preserves_leading_zero(tmp_path):
    """Select catalog metadata by exact names including leading zeros."""
    instance = tournament(tmp_path, domains=["01", "paper-domain"])
    output = tmp_path / "results"
    output.mkdir()
    instance._domain_metadata = pd.DataFrame({"DomainName": ["other", "paper-domain", "01"],
                                              "Size": [9, 3, 2], "Unnamed: 0": [3, 1, 2]},
                                             index=[99, 80, 70])
    instance.extract_domains()
    result = pd.read_excel(output / "domains.xlsx", dtype={"DomainName": str})
    assert set(result["DomainName"]) == {"01", "paper-domain"}
    assert set(result["Size"]) == {2, 3}
    assert not any(name.startswith("Unnamed") for name in result.columns)


def test_missing_selected_catalog_name_preserves_old_results(tmp_path, monkeypatch):
    """Retain prior output when a selected domain is absent from the catalog."""
    module = importlib.import_module("nenv.Tournament")
    instance = tournament(tmp_path)
    output = tmp_path / "results"
    output.mkdir()
    marker = output / "previous.txt"
    marker.write_text("preserve")
    monkeypatch.setattr(module.pd, "read_excel", lambda *args, **kwargs: pd.DataFrame({"DomainName": ["other"]}))
    with pytest.raises(ValueError, match="catalog"):
        instance.run()
    assert marker.read_text() == "preserve"


def test_cancellation_during_preflight_preserves_old_results(tmp_path, monkeypatch):
    """Honor cancellation during profile checks before replacing prior output."""
    manager = importlib.import_module("nenv.SessionManager")
    original_loader = manager.domain_loader
    instance = tournament(tmp_path)
    output = tmp_path / "results"
    output.mkdir()
    marker = output / "previous.txt"
    marker.write_text("preserve")

    def cancel_when_profiles_load(name):
        """Request cancellation while preserving normal profile loading."""
        instance.killed = True
        return original_loader(name)

    monkeypatch.setattr(manager, "domain_loader", cancel_when_profiles_load)
    instance.run()
    assert instance.cancelled and instance.failure is None
    assert not instance.tournament_process.is_active
    assert marker.read_text() == "preserve"


def test_cancellation_before_first_session_does_not_construct_agents(tmp_path, monkeypatch):
    """Skip agent construction when cancellation precedes the first session."""
    module = importlib.import_module("nenv.Tournament")
    instance = tournament(tmp_path)
    original_combinations = instance.generate_combinations

    def cancel_after_combinations():
        """Request cancellation immediately after generating the schedule."""
        instance.killed = True
        return original_combinations()

    monkeypatch.setattr(instance, "generate_combinations", cancel_after_combinations)
    monkeypatch.setattr(module, "SessionManager", lambda *args, **kwargs: pytest.fail("Cancelled session started."))
    instance.run()
    assert instance.cancelled and instance.failure is None
    assert instance.tournament_process.completed_number_of_sessions == 0


def test_distinct_agent_classes_with_the_same_name_can_negotiate(tmp_path):
    """Schedule distinct classes independently of their shared display name."""
    left = type("Twin", (BoulwareAgent,), {"__module__": "left"})
    right = type("Twin", (ConcederAgent,), {"__module__": "right"})
    instance = tournament(tmp_path, agent_classes=[left, right])
    assert instance.generate_combinations() == [(left, right, "0"), (right, left, "0")]


def test_numpy_integer_seed_runs_with_public_numeric_contract(tmp_path, monkeypatch):
    """Run a tournament after converting an accepted NumPy integer seed."""
    module = importlib.import_module("nenv.Tournament")
    monkeypatch.setattr(module, "open_folder", lambda path: None)
    instance = tournament(tmp_path, seed=np.int64(7))
    # random.seed requires the built-in type rather than an integer scalar wrapper.
    assert type(instance.seed) is int  # pylint: disable=unidiomatic-typecheck
    instance.run()
    assert instance.failure is None
    assert instance.tournament_process.is_completed


def test_cli_reports_invalid_configuration_with_nonzero_status(tmp_path, monkeypatch, capsys):
    """Report invalid CLI settings with an error message and nonzero exit status."""
    path = tmp_path / "invalid.yaml"
    path.write_text("agents: []\ndomains: [0]\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run.py", str(path)])
    script = Path(__file__).resolve().parents[1] / "run.py"
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(script), run_name="__main__")
    assert error.value.code == 1
    assert "Tournament failed:" in capsys.readouterr().err
