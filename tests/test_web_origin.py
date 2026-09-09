"""Keep local plugin imports behind the bundled Web interface's origin."""
import sys

import pytest

import app as web
from nenv.utils.DynamicImport import load_agent_class


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    marker = tmp_path / "imported.txt"
    module = tmp_path / "origin_probe_plugin.py"
    module.write_text(
        'from pathlib import Path\n'
        'from agents import BoulwareAgent\n'
        'Path(__file__).with_name("imported.txt").write_text("imported")\n'
        'class LocalAgent(BoulwareAgent):\n'
        '    pass\n', encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("origin_probe_plugin", None)
    yield "origin_probe_plugin.LocalAgent", marker
    sys.modules.pop("origin_probe_plugin", None)


@pytest.mark.parametrize("headers", [
    {"Origin": "https://untrusted.example"},
    {"Origin": "null"},
    {"Origin": "http://localhost:5001"},
    {"Origin": "https://localhost"},
    {"Sec-Fetch-Site": "cross-site"},
    {"Sec-Fetch-Site": "same-site"},
    {"Host": "untrusted.example"},
    {"Host": "localhost.untrusted.example"},
])
def test_foreign_web_request_is_rejected_before_plugin_import(plugin, headers):
    path, marker = plugin
    response = web.app.test_client().post("/check/agent_path", json={"path": path}, headers=headers)
    assert response.status_code == 403
    assert response.get_json()["error"]
    assert not marker.exists()
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.parametrize("base_url,headers", [
    ("http://localhost", {}),
    ("http://localhost", {"Origin": "http://localhost"}),
    ("http://127.0.0.1:5001", {"Origin": "http://127.0.0.1:5001", "Sec-Fetch-Site": "same-origin"}),
    ("http://localhost:5001", {"Origin": "http://localhost:5001"}),
    ("http://[::1]:5001", {"Origin": "http://[::1]:5001"}),
    ("http://localhost:80", {"Origin": "http://localhost"}),
])
def test_local_operator_can_load_trusted_plugins(plugin, base_url, headers):
    path, marker = plugin
    response = web.app.test_client().post("/check/agent_path", base_url=base_url,
                                          json={"path": path}, headers=headers)
    assert response.status_code == 200
    assert not response.get_json()["error"]
    assert response.get_json()["class_name"] == "LocalAgent"
    assert marker.read_text() == "imported"


def test_nonbrowser_python_plugin_loading_is_unchanged(plugin):
    path, marker = plugin
    selected = load_agent_class(path)
    assert selected.__name__ == "LocalAgent"
    assert marker.read_text() == "imported"


def test_cross_origin_preflight_does_not_enable_plugin_requests():
    response = web.app.test_client().options("/check/agent_path", headers={
        "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"})
    assert response.status_code == 403
    assert "Access-Control-Allow-Origin" not in response.headers
