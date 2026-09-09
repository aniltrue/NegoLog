"""Exercise public row iteration and assignment independently of Excel output."""

from collections import UserDict
from pathlib import Path
# The regression uses only this interpreter and a fixed local script.
import subprocess  # nosec B404
import sys

import pytest

from nenv.utils.ExcelLog import ExcelLog


@pytest.mark.parametrize("sheet_count,row_count", [(1, 4), (4, 1), (3, 0)])
def test_iteration_follows_rows_instead_of_sheet_count(sheet_count, row_count):
    """Iterate over log rows independently of the number of sheets."""
    log = ExcelLog([str(index) for index in range(sheet_count)])
    for index in range(row_count):
        log.append({"0": {"Value": index}})
    rows = list(log)
    assert len(rows) == row_count
    assert len(log) == row_count
    assert [row["0"]["Value"] for _, row in rows] == list(range(row_count))


def test_iteration_preserves_empty_cells_in_unequal_sheets():
    """Preserve row alignment when sheet lengths differ."""
    log = ExcelLog(["A", "B"])
    log.log_rows = {"A": [{"Value": 1}], "B": [{}, {"Value": 2}, {"Value": 3}]}
    assert list(log) == [(0, {"A": {"Value": 1}, "B": {}}),
                         (1, {"A": {}, "B": {"Value": 2}}),
                         (2, {"A": {}, "B": {"Value": 3}})]
    assert len(log) == 3


def test_append_new_sheet_pads_existing_rows():
    """Pad earlier rows when an appended record introduces a new sheet."""
    log = ExcelLog(["Session"])
    log.append({"Session": {"Round": 0}})
    log.append({"Session": {"Round": 1}, "Late": {"Value": 9}})
    assert log.log_rows["Late"] == [{}, {"Value": 9}]
    assert len(log) == 2


def test_update_new_sheet_targets_current_row():
    """Align a newly updated sheet with the current log row."""
    log = ExcelLog(["Session"])
    log.append({"Session": {"Round": 0}})
    log.append({"Session": {"Round": 1}})
    log.update({"Late": {"Value": 9}})
    assert log.log_rows["Late"] == [{}, {"Value": 9}]
    assert log.log_rows["Session"] == [{"Round": 0}, {"Round": 1}]


def test_update_empty_log_creates_first_row():
    """Create the first row when updating an empty log."""
    log = ExcelLog()
    log.update({"Session": {"Round": 0}})
    assert list(log) == [(0, {"Session": {"Round": 0}})]


def test_all_documented_assignment_forms_preserve_other_cells():
    """Retain unrelated cell values across all supported assignment forms."""
    log = ExcelLog(["Session"])
    log.append({"Session": {"Value": 1, "Keep": 7}})
    log[0] = {"Session": {"Value": 2}}
    log[0, "Session"] = {"Value": 3}
    log[0, "Session", "Value"] = 4
    assert log[0, "Session"] == {"Value": 4, "Keep": 7}


@pytest.mark.parametrize("key,value", [(0, 3), (0, UserDict({"Session": {"Value": 9}})),
                                      ((0, "Session"), 3), ((0, "Session"), [("Value", 9)])])
def test_row_assignment_requires_dictionary_values(key, value):
    """Require dictionaries for row assignments without changing existing cells."""
    log = ExcelLog(["Session"])
    log.append({"Session": {"Value": 1}})
    with pytest.raises(TypeError):
        log[key] = value
    assert log[0, "Session"] == {"Value": 1}


def test_row_assignment_validation_survives_optimized_python():
    """Reject iterable replacements even when Python removes assert statements."""
    script = """
from collections import UserDict
from nenv.utils.ExcelLog import ExcelLog

for key, value in [(0, UserDict({"Session": {"Value": 9}})),
                   ((0, "Session"), [("Value", 9)])]:
    log = ExcelLog(["Session"])
    log.append({"Session": {"Value": 1}})
    try:
        log[key] = value
    except TypeError:
        if log[0, "Session"] != {"Value": 1}:
            raise RuntimeError("Rejected assignment modified the log.")
    else:
        raise RuntimeError("Optimized Python accepted a non-dictionary assignment.")
"""
    # No shell or external command input: exercise a fixed optimized-Python fixture.
    result = subprocess.run([sys.executable, "-O", "-c", script],  # nosec B603
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
