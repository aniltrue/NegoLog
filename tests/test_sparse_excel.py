"""Selected-sheet serialization is optional and does not alter stored logs."""
from copy import deepcopy

import pandas as pd
import pytest

from nenv.utils.ExcelLog import ExcelLog


@pytest.fixture
def log():
    result = ExcelLog(["Session", "Measurements", "Empty"])
    result.log_rows = {
        "Session": [{"Round": 0, "Utility": 0.5}, {}, {"Round": 2, "Utility": 0.75}],
        "Measurements": [
            {"Round": 0, "Value": 0, "Enabled": False},
            {},
            {"Round": 2, "Value": None, "Enabled": False},
        ],
        "Empty": [{}, {}],
    }
    return result


@pytest.mark.parametrize("options", [{}, {"sparse_sheets": set()}])
def test_default_save_preserves_dense_rows(log, tmp_path, options):
    path = tmp_path / "dense.xlsx"
    log.save(str(path), **options)

    sheets = pd.read_excel(path, sheet_name=None)
    assert set(sheets) == log.sheet_names
    for name in ("Session", "Measurements"):
        pd.testing.assert_frame_equal(
            sheets[name], pd.DataFrame(log.log_rows[name]), check_dtype=False
        )
    assert sheets["Empty"].empty


def test_only_selected_sheets_drop_empty_rows(log, tmp_path):
    before = deepcopy(log.log_rows)
    path = tmp_path / "selected.xlsx"
    log.save(str(path), sparse_sheets={"Measurements", "Empty"})

    sheets = pd.read_excel(path, sheet_name=None)
    assert len(sheets["Session"]) == 3
    assert sheets["Session"].iloc[1].isna().all()
    measurements = sheets["Measurements"]
    assert measurements["Round"].tolist() == [0, 2]
    assert measurements.loc[0, "Value"] == 0
    assert pd.isna(measurements.loc[1, "Value"])
    assert measurements["Enabled"].tolist() == [False, False]
    assert sheets["Empty"].empty
    assert log.log_rows == before


def test_sparse_save_does_not_change_later_dense_save(log, tmp_path):
    log.save(str(tmp_path / "selected.xlsx"), sparse_sheets={"Measurements"})
    path = tmp_path / "dense.xlsx"
    log.save(str(path))

    measurements = pd.read_excel(path, sheet_name="Measurements")
    assert len(measurements) == 3
    assert measurements.iloc[1].isna().all()
