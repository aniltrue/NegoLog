"""Domain previews, catalog updates and exports preserve saved inputs."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

import app as web
from domain_generator import domain_generator as generator
from domain_generator.domain_storage import read_catalog, upsert_catalog
from nenv import Preference


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Isolate domain storage and replace plotting with a deterministic image."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(generator.plt, "savefig", lambda filename, **kwargs: Path(filename).write_bytes(b"preview-png"))
    monkeypatch.setattr(web, "_preview_images", {})
    monkeypatch.setattr(web, "_running_tournaments", set())
    web.app.config.update(TESTING=True)
    return tmp_path, web.app.test_client()


def profile():
    """Return a minimal valid profile for domain editing."""
    return {"issueWeights": {"price": 1.}, "issues": {"price": {"low": .2, "high": 1.}}, "reservationValue": 0.}


def create(name="1"):
    """Generate and register one domain in the isolated catalog."""
    data = profile()
    result = generator.generate_domain(name, data["issueWeights"], data["issueWeights"], data["issues"], data["issues"])
    upsert_catalog(result)
    return result


def snapshot(root):
    """Capture file contents to detect unintended storage changes."""
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_preview_never_changes_saved_domain_or_catalog(workspace):
    """Update a preview image without changing stored domain or catalog files."""
    root, client = workspace
    create()
    original = snapshot(root)
    changed = profile()
    changed["issues"]["price"]["low"] = .8
    response = client.post("/edit/domain", json={"name": "1", "profileA": changed, "profileB": profile(), "save": False}).get_json()
    assert not response["error"]
    assert snapshot(root) == original
    image = client.get("/fetch/bid_space/domain1")
    assert image.data == b"preview-png"
    assert image.headers["Cache-Control"] == "no-store"


def test_saved_edit_upserts_one_row_and_preserves_other_ids(workspace):
    """Replace a saved domain row while preserving distinct string identifiers."""
    _, client = workspace
    for name in ["0", "1", "001", "2"]:
        create(name)
    changed = profile()
    changed["issues"]["price"]["low"] = .7
    for _ in range(2):
        result = client.post("/edit/domain", json={"name": "1", "profileA": changed, "profileB": profile(), "save": True}).get_json()
        assert not result["error"]
    assert sorted(read_catalog()["DomainName"]) == ["0", "001", "1", "2"]
    saved = json.loads(Path("domains/domain1/profileA.json").read_text())
    assert saved["issues"]["price"]["low"] == .7


def test_manual_creation_and_string_id_removal_update_catalog(workspace):
    """Keep manual creation and string-identifier removal reflected in the catalog."""
    _, client = workspace
    result = client.post("/create/domain", json={"name": "10", "numberOfIssues": 1, "numberOfValuesPerIssue": {"0": 2}}).get_json()
    assert not result["error"]
    assert list(read_catalog()["DomainName"]) == ["10"]
    assert not client.post("/remove/domains", json={"domainNames": ["10"]}).get_json()["error"]
    assert read_catalog().empty
    assert not Path("domains/domain10").exists()


@pytest.mark.parametrize("change", ["invalid_profile", "invalid_save", "invalid_name"])
def test_rejected_edit_preserves_all_files(workspace, change):
    """Reject invalid edit requests before changing any saved files."""
    root, client = workspace
    create()
    original = snapshot(root)
    data = {"name": "1", "profileA": profile(), "profileB": profile(), "save": True}
    if change == "invalid_profile":
        data["profileB"]["issues"] = {}
    elif change == "invalid_save":
        data["save"] = "false"
    else:
        data["name"] = "../escape"
    assert client.post("/edit/domain", json=data).get_json()["error"]
    assert snapshot(root) == original


def test_plot_failure_keeps_prior_domain(workspace, monkeypatch):
    """Retain the previous domain when staged plotting fails."""
    root, _ = workspace
    create()
    original = snapshot(root)

    def fail_plot(*args, **kwargs):
        """Simulate plot generation failure before replacing saved output."""
        raise OSError("plot unavailable")
    monkeypatch.setattr(generator.plt, "savefig", fail_plot)
    with pytest.raises(OSError, match="plot unavailable"):
        create()
    assert snapshot(root) == original
    generator.plt.close("all")


def test_default_random_utility_range_and_relative_genius_export(workspace):
    """Generate default utility ranges and valid relative Genius exports."""
    for genius in [False, True]:
        result = generator.generate_random_domain("sample", 1, 2, has_randomness=False, is_for_genius=genius)
        assert result["Size"] == 2
        root = Path("domains_genius" if genius else "domains") / "domainsample"
        assert (root / "profileA.json").exists()
        if genius:
            data = json.loads((root / "specials.json").read_text())
            assert len(data["pareto_front"]) == 1
            assert data["pareto_front"][0]["utility"] == [1., 1.]


def test_constraints_are_not_relaxed_and_failure_preserves_domain(workspace):
    """Bound failed generation without widening ranges or replacing stored inputs."""
    root, _ = workspace
    create()
    original = snapshot(root)
    opposition = [2., 3.]
    before = copy.deepcopy(opposition)
    with pytest.raises(ValueError, match="3 attempts"):
        generator.generate_random_domain("1", 1, 2, has_randomness=False, opposition_range=opposition, max_attempts=3)
    assert opposition == before
    assert snapshot(root) == original
    with pytest.raises(ValueError, match="2 attempts"):
        generator.generate_random_domain("1", 2, 2, domain_size_range=[1, 2], max_attempts=2)
    assert snapshot(root) == original


def test_normalization_is_bounded_and_bid_limit_never_returns_partial_bids():
    """Normalize issue weights and require complete bid enumeration within limits."""
    preference = generator.Preference([2] * 10, False, has_randomness=False)
    assert sum(preference.issue_weights.values()) == pytest.approx(1.)
    with pytest.raises(ValueError, match="complete bid space"):
        preference.generate_bids(100)
    assert all(len(bid) == 10 for bid in preference.generate_bids(1024))


def test_genius_front_indices_match_their_bids():
    """Match each exported Pareto utility pair to its actual bid."""
    first = generator.Preference([3], False, has_randomness=False)
    second = generator.Preference([3], True, has_randomness=False)
    second.issues["issueA"] = {"valueA": 1., "valueB": 0., "valueC": .2}
    result = generator.convert2genius_specs({"Opposition": .2}, first, second)
    assert len(result["pareto_front"]) == 2
    for point in result["pareto_front"]:
        assert point["utility"] == [first.get_utility(point["bid"]), second.get_utility(point["bid"])]


def test_zero_product_nash_returns_an_actual_point():
    """Return an existing Nash candidate when every utility product is zero."""
    points = np.array([[0., .8], [0., .2]])
    nash, _, index, _ = generator.find_nash_kalai(points)
    assert list(nash) == list(points[index]) == [0., .8]


def test_saved_profiles_and_specs_describe_same_utilities(workspace):
    """Match saved profile utilities to the reported domain statistics."""
    raw = {"price": {"low": 2., "high": 4.}}
    result = generator.generate_domain("scaled", {"price": 1.}, {"price": 1.}, raw, raw)
    saved = Preference("domains/domainscaled/profileA.json")
    assert max(bid.utility for bid in saved.bids) == result["MaxUtility"]
    assert min(bid.utility for bid in saved.bids) == result["MinUtility"]


def test_random_domain_form_accepts_numeric_strings_from_existing_ui(workspace):
    """Keep edited browser form values compatible with the typed generator API."""
    _, client = workspace
    config = {"name": "browser", "numberOfDomains": "1", "issue_size_range": ["1", "1"],
              "value_size_range": ["2", "2"], "utility_range": ["0.0", "1.0"],
              "opposition_range": ["0", "1"], "balance_score_range": ["0", "0.05"],
              "reservation_value_profile_a": "0.1", "reservation_value_profile_b": "0.2",
              "has_randomness": False}
    result = client.post("/create/domains", json={"config": config}).get_json()
    assert not result["error"]
    assert result["domains"][0]["RealName"] == "browser"
    assert result["domains"][0]["ReservationValueA"] == .1
    assert list(read_catalog()["DomainName"]) == ["browser"]


def test_domain_removal_rolls_back_if_catalog_cannot_be_written(workspace, monkeypatch):
    """Retain domain folders when updating the catalog fails during removal."""
    from domain_generator import domain_storage
    root, client = workspace
    create()
    original = snapshot(root)

    def fail_write(*args, **kwargs):
        """Simulate a catalog write failure before publishing the domain change."""
        raise OSError("catalog is unavailable")
    monkeypatch.setattr(domain_storage, "write_catalog", fail_write)
    assert client.post("/remove/domains", json={"domainNames": ["1"]}).get_json()["error"]
    assert snapshot(root) == original


def test_saved_edit_keeps_profiles_if_catalog_write_fails(workspace, monkeypatch):
    """Rollback the complete saved domain when staging its catalog fails."""
    from domain_generator import domain_storage
    root, client = workspace
    create()
    original = snapshot(root)

    def fail_write(*args, **kwargs):
        """Simulate a catalog write failure before publishing the domain change."""
        raise OSError("catalog unavailable")
    monkeypatch.setattr(domain_storage, "write_catalog", fail_write)
    changed = profile()
    changed["issues"]["price"]["low"] = .9
    result = client.post("/edit/domain", json={"name": "1", "profileA": changed, "profileB": profile(), "save": True}).get_json()
    assert result["error"]
    assert snapshot(root) == original


def test_saved_edit_rolls_back_if_catalog_publication_fails(workspace, monkeypatch):
    """Restore the previous folder when the final catalog rename fails."""
    root, client = workspace
    create()
    original = snapshot(root)
    replace = Path.replace

    def fail_catalog_replace(source, target):
        """Simulate failure when replacing the staged domain catalog workbook."""
        if Path(target) == Path("domains/domains.xlsx"):
            raise OSError("catalog locked")
        return replace(source, target)
    monkeypatch.setattr(Path, "replace", fail_catalog_replace)
    changed = profile()
    changed["issues"]["price"]["low"] = .9
    result = client.post("/edit/domain", json={"name": "1", "profileA": changed, "profileB": profile(), "save": True}).get_json()
    assert result["error"]
    assert snapshot(root) == original
