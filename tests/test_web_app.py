"""Local web entry points must expose loadable concrete agents and assets."""
import json
from pathlib import Path

import pytest

import app as web
from agents import BoulwareAgent, ConcederAgent
from nenv import Tournament
from nenv.utils.DynamicImport import load_agent_class


@pytest.fixture
def client(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    web.app.config.update(TESTING=True)
    return web.app.test_client()


def test_home_page_and_bundled_assets_are_served(client):
    assert client.get("/").status_code == 200
    manifest = json.loads(client.get("/asset-manifest.json").data)
    for path in manifest["entrypoints"]:
        assert client.get("/" + path).status_code == 200


def test_agent_catalog_contains_only_loadable_concrete_agents(client):
    data = client.get("/fetch/agents").get_json()
    assert not data["error"]
    assert len(data["agents"]) == 28
    assert {"CBOMAgent", "CBOMJavaAgent"} <= data["agents"].keys()
    assert "AbstractAgent" not in data["agents"]
    for path in data["agents"].values():
        load_agent_class(path)


def test_discovery_skips_private_implementation_and_cli_entrypoints(client, monkeypatch):
    paths = ["agents/CBOM/_vendor/cbom/__main__.py", "agents/CBOM/_vendor/cbom/model.py",
             "agents/CBOM/__main__.py", "agents/CBOM/__init__.py"]
    monkeypatch.setattr(web.glob, "glob", lambda *args, **kwargs: paths)
    data = client.get("/fetch/agents").get_json()
    assert not data["error"]
    assert set(data["agents"]) == {"CBOMAgent", "CBOMJavaAgent"}


@pytest.mark.parametrize("filename", ["agents/boulware/Boulware.py", r"agents\boulware\Boulware.py"])
def test_discovery_handles_both_platform_path_separators(client, monkeypatch, filename):
    monkeypatch.setattr(web.glob, "glob", lambda *args, **kwargs: [filename])
    data = client.get("/fetch/agents").get_json()
    assert not data["error"]
    assert data["agents"]["BoulwareAgent"] == "agents.boulware.Boulware.BoulwareAgent"


def test_domain_and_configuration_catalogs_load(client):
    domains = client.get("/fetch/domains").get_json()
    assert not domains["error"] and domains["domains"]
    settings = client.get("/fetch/tournament_configurations").get_json()
    assert not settings["error"] and settings["settings"]


def test_newly_registered_tournament_can_be_polled_before_thread_starts(client, monkeypatch, tmp_path):
    tournament = Tournament([BoulwareAgent, ConcederAgent], ["0"], [], [], None, 8,
                            result_dir=str(tmp_path / "run"))
    monkeypatch.setattr(web, "tournaments", {"pending.yaml": tournament})
    data = client.get("/fetch/tournaments").get_json()
    assert not data["error"]
    pending = data["tournaments"][0]
    assert pending["status"] == "Pending"
    assert pending["start_time"] == pending["last_update"] == "TBD"
    assert pending["completed_percentage"] == "0.00 %"
