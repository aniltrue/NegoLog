"""Web tournament lifecycle uses the validated public configuration path."""
from pathlib import Path

import pytest
import yaml

import app as web


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provide an isolated web client with one valid tournament configuration."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(web, "tournaments", {})
    monkeypatch.setattr(web, "_running_tournaments", set())
    web.app.config.update(TESTING=True)
    root = Path("tournament_configurations")
    root.mkdir()
    config = {"agents": ["BoulwareAgent", "ConcederAgent"], "domains": ["0"], "deadline_round": 8}
    (root / "valid.yaml").write_text(yaml.safe_dump(config))
    return web.app.test_client()


def test_invalid_config_does_not_hide_valid_settings(client):
    """List valid settings even when another configuration file is malformed."""
    Path("tournament_configurations/broken.yaml").write_text("- not a mapping")
    data = client.get("/fetch/tournament_configurations").get_json()
    assert not data["error"]
    assert len(data["settings"]) == len(data["invalidSettings"]) == 1
    assert data["settings"][0]["name"].replace("\\", "/").endswith("valid.yaml")
    assert data["settings"][0]["loggers"] == []


def test_invalid_config_is_not_saved(client):
    """Reject invalid web configuration without creating a settings file."""
    response = client.post("/create/tournament_configuration", json={"config": {"name": "invalid", "agents": []}})
    assert response.get_json()["error"]
    assert not Path("tournament_configurations/invalid.yaml").exists()


def test_config_removal_stays_within_settings_directory(client):
    """Keep configuration removal inside the designated settings directory."""
    target = Path("keep.yaml")
    target.write_text("keep")
    assert client.post("/remove/tournament_configuration", json={"name": str(target)}).get_json()["error"]
    assert target.read_text() == "keep"


@pytest.mark.parametrize("route,path", [("agent", "nenv.AbstractAgent"), ("logger", "nenv.Preference"),
                                        ("opp_model", "nenv.OpponentModel.AbstractOpponentModel")])
def test_path_checks_reject_abstract_or_wrong_component_types(client, route, path):
    """Reject invalid component types through the web validation routes."""
    assert client.post(f"/check/{route}_path", json={"path": path}).get_json()["error"]


def delayed_threads(monkeypatch):
    """Capture background jobs so tests control their start time."""
    jobs = []

    class DelayedThread:
        """Defer a background target until the test explicitly executes it."""

        def __init__(self, target, args, daemon):
            """Capture the target call without starting a background thread."""
            jobs.append(lambda: target(*args))

        def start(self):
            """Leave the captured job pending for deterministic lifecycle checks."""
    monkeypatch.setattr(web.threading, "Thread", DelayedThread)
    return jobs


def test_pending_tournament_reserves_slot_and_cancel_is_not_lost(client, monkeypatch):
    """Reserve the active slot and retain cancellation before a job starts."""
    jobs = delayed_threads(monkeypatch)
    request = {"path": "tournament_configurations/valid.yaml"}
    assert not client.post("/start/tournament", json=request).get_json()["error"]
    assert client.post("/start/tournament", json=request).get_json()["error"]
    assert client.post("/remove/domains", json={"domainNames": ["0"]}).get_json()["error"]
    tournament = web.tournaments[request["path"]]
    assert not client.post("/remove/tournament", json=request).get_json()["error"]
    assert web._running_tournaments
    jobs[0]()
    assert tournament.cancelled
    assert not web._running_tournaments
    assert not Path("results").exists()


def test_background_failure_is_visible_and_releases_slot(client, monkeypatch):
    """Expose background failures and release the active tournament slot."""
    jobs = delayed_threads(monkeypatch)
    assert not client.post("/start/tournament", json={"path": "tournament_configurations/valid.yaml"}).get_json()["error"]
    jobs[0]()  # The isolated workspace deliberately has no domain catalog.
    response = client.get("/fetch/tournaments").get_json()
    assert not response["error"]
    record = response["tournaments"][0]
    assert record["status"] == "Error"
    assert "domains.xlsx" in record["errorMessage"]
    assert not web._running_tournaments


def test_settings_editor_boolean_strings_are_saved_as_yaml_booleans(client):
    """Preserve the bundled editor's select values at the Web boundary."""
    config = {"name": "editor", "agents": ["BoulwareAgent"], "domains": ["0"],
              "deadline_round": 8, "shuffle": "false", "self_negotiation": "true"}
    result = client.post("/create/tournament_configuration", json={"config": config}).get_json()
    assert not result["error"]
    saved = yaml.safe_load(Path("tournament_configurations/editor.yaml").read_text())
    assert saved["shuffle"] is False
    assert saved["self_negotiation"] is True


def test_legacy_web_settings_with_boolean_strings_remain_runnable(client, monkeypatch):
    """Load files saved by the older editor without weakening the CLI schema."""
    jobs = delayed_threads(monkeypatch)
    path = Path("tournament_configurations/legacy.yaml")
    path.write_text(yaml.safe_dump({"agents": ["BoulwareAgent"], "domains": ["0"], "deadline_round": 8,
                                   "shuffle": "false", "self_negotiation": "true"}))
    result = client.post("/start/tournament", json={"path": str(path)}).get_json()
    assert not result["error"]
    assert len(jobs) == 1
    settings = client.get("/fetch/tournament_configurations").get_json()
    assert not settings["invalidSettings"]
