"""Missing values from one logger must not erase another logger's results."""
import math
from types import SimpleNamespace

import pytest

from nenv.logger.EstimatedBidSpaceLogger import EstimatedBidSpaceLogger
from nenv.logger.EstimatedParetoLogger import EstimatedParetoLogger
from nenv.utils.ExcelLog import ExcelLog


@pytest.mark.parametrize("logger_class,columns", [
    (EstimatedParetoLogger, ["PrecisionA", "RecallA", "F1A", "PrecisionB", "RecallB", "F1B"]),
    (EstimatedBidSpaceLogger, ["EstimatedNashDistanceA", "EstimatedNashDistanceB",
                               "EstimatedKalaiDistanceA", "EstimatedKalaiDistanceB"]),
])
@pytest.mark.parametrize("roundtrip", [False, True])
def test_unrelated_missing_ranks_do_not_change_other_metric_summaries(tmp_path, logger_class, columns, roundtrip):
    workbook = ExcelLog(["Model"])
    for value in [.25, .75]:
        workbook.append({"Model": {**dict.fromkeys(columns, value),
                                    "SpearmanA": math.nan, "KendallTauA": math.nan}})
    # A row missing one of this logger's own measurements still follows the
    # existing complete-measurement policy and must not affect its mean.
    workbook.append({"Model": {**dict.fromkeys(columns, .9), columns[0]: math.nan,
                                "SpearmanA": 1., "KendallTauA": 1.}})
    if roundtrip:
        path = tmp_path / "metrics.xlsx"
        workbook.save(str(path))
        workbook = ExcelLog(file_path=str(path))
    session = SimpleNamespace(agentA=SimpleNamespace(estimators=[SimpleNamespace(name="Model")]),
                              session_log=workbook)
    result = logger_class(str(tmp_path)).on_session_end({}, session)["Model"]
    for column in columns:
        assert result[column] == pytest.approx(.5)
    assert math.isnan(workbook.log_rows["Model"][0]["SpearmanA"])
    assert len(workbook.log_rows["Model"]) == 3


@pytest.mark.parametrize("logger_class", [EstimatedParetoLogger, EstimatedBidSpaceLogger])
@pytest.mark.parametrize("other_metrics_only", [False, True])
def test_empty_or_unmeasured_sheet_keeps_zero_summary(tmp_path, logger_class, other_metrics_only):
    workbook = ExcelLog(["Model"])
    if other_metrics_only:
        workbook.append({"Model": {"SpearmanA": math.nan, "RMSE_A": .25}})
    session = SimpleNamespace(agentA=SimpleNamespace(estimators=[SimpleNamespace(name="Model")]),
                              session_log=workbook)
    result = logger_class(str(tmp_path)).on_session_end({}, session)["Model"]
    assert all(value == 0. for value in result.values())
