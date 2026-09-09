"""Optional metric sampling and keyed histories through real Excel workbooks."""
import json
import math
from types import SimpleNamespace

import pytest

from nenv import Preference
from nenv.OpponentModel import AbstractOpponentModel
from nenv.SessionLogs import SessionLogs
from nenv.logger.EstimatorMetricLogger import EstimatorMetricLogger
from nenv.utils.ExcelLog import ExcelLog


METRIC_COLUMNS = {
    "RMSE_A", "RMSE_B", "SpearmanA", "SpearmanB", "KendallTauA", "KendallTauB",
    "RMSE", "Spearman", "KendallTau",
}


class CountingModel(AbstractOpponentModel):
    """A public API extension with observable measurement and update calls."""

    def __init__(self, preference, name="Model", values=(.1, .2, .3)):
        """Initialize fixed metrics and counters for sampling assertions."""
        super().__init__(preference)
        self.model_name = name
        self.values = values
        self.measurements = 0
        self.updates = 0

    @property
    def name(self):
        return self.model_name

    def update(self, bid, time):
        self.updates += 1

    def calculate_error(self, reference, return_rmse=True, return_spearman=True, return_kendall_tau=True,
                        *, vectorized=False):
        self.measurements += 1
        return self.values


@pytest.fixture
def session(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "reservationValue": 0,
        "issueWeights": {"color": .7, "size": .3},
        "issues": {"color": {"red": 1., "blue": .2}, "size": {"small": .4, "large": 1.}},
    }))
    agents = []
    for values in [(.1, .2, .3), (.4, .5, .6)]:
        preference = Preference(str(path))
        agents.append(SimpleNamespace(preference=preference, estimators=[CountingModel(preference, values=values)]))
    return SimpleNamespace(agentA=agents[0], agentB=agents[1], round=0)


def tournament(round_number):
    result = ExcelLog(["TournamentResults"])
    result.append({"TournamentResults": {
        "AgentA": "A", "AgentB": "B", "DomainName": "1", "Round": round_number,
    }})
    return result


def metrics(value):
    return {"RMSE_A": value, "RMSE_B": value + 1,
            "SpearmanA": value + 2, "SpearmanB": value + 3,
            "KendallTauA": value + 4, "KendallTauB": value + 5}


@pytest.mark.parametrize("interval", [0, -1, True, 1.5, "2", None])
def test_sampling_interval_must_be_a_positive_integer(tmp_path, interval):
    with pytest.raises(ValueError, match="positive integer"):
        EstimatorMetricLogger(str(tmp_path), sample_every=interval)


def test_default_callbacks_keep_every_measurement_and_old_columns(session, tmp_path):
    logger = EstimatorMetricLogger(str(tmp_path))
    bid = session.agentA.preference.bids[0]
    del session.round  # Existing default callers do not need the new metadata.
    for callback in [lambda: logger.on_offer("A", bid, .1, session),
                     lambda: logger.on_offer("B", bid, .2, session),
                     lambda: logger.on_accept("B", bid, .3, session),
                     lambda: logger.on_fail(.4, session)]:
        row = callback()["Model"]
        assert set(row) == METRIC_COLUMNS
        assert (row["RMSE_A"], row["SpearmanA"], row["KendallTauA"]) == (.1, .2, .3)
        assert (row["RMSE_B"], row["SpearmanB"], row["KendallTauB"]) == (.4, .5, .6)
        assert row["RMSE"] == pytest.approx(.25)
    assert session.agentA.estimators[0].measurements == 4
    assert session.agentB.estimators[0].measurements == 4


@pytest.mark.parametrize("interval", [2, 3])
def test_custom_interval_skips_only_offer_metrics_and_keeps_terminal_state(session, tmp_path, interval):
    logger = EstimatorMetricLogger(str(tmp_path), sample_every=interval)
    bid = session.agentA.preference.bids[0]
    measured_rounds = []
    for round_number in range(7):
        session.round = round_number
        for side in ["A", "B"]:
            result = logger.on_offer(side, bid, round_number / 10, session)
            if round_number % interval:
                assert result == {}
            else:
                assert result["Model"]["Round"] == round_number
                assert result["Model"]["Action"] == "Offer"
                measured_rounds.append(round_number)
    assert measured_rounds == [r for r in range(7) if r % interval == 0 for _ in range(2)]
    session.round = 7  # An unsampled round must still produce final metrics.
    assert logger.on_accept("B", bid, .9, session)["Model"]["Action"] == "Accept"
    failure = logger.on_fail(1., session)["Model"]
    assert failure["Round"] == 7
    assert failure["Action"] == "Fail"
    assert session.agentA.estimators[0].measurements == len(measured_rounds) + 2
    assert session.agentB.estimators[0].measurements == len(measured_rounds) + 2


def test_metadata_can_be_enabled_without_sampling(session, tmp_path):
    logger = EstimatorMetricLogger(str(tmp_path), include_round=True)
    session.round = 5
    result = logger.on_offer("A", session.agentA.preference.bids[0], .5, session)["Model"]
    assert set(result) == METRIC_COLUMNS | {"Round", "Action"}
    assert result["Round"] == 5
    assert result["Action"] == "Offer"
    assert set(logger.get_metrics(session.agentA, session.agentB)["Model"]) == METRIC_COLUMNS


@pytest.mark.parametrize("interval,sparse", [(1, False), (2, False), (3, False), (3, True)])
def test_callback_sampling_survives_excel_roundtrip(session, tmp_path, interval, sparse):
    (tmp_path / "sessions").mkdir()
    logger = EstimatorMetricLogger(str(tmp_path), sample_every=interval)
    workbook = ExcelLog(["Session", "Model"])
    bid = session.agentA.preference.bids[0]
    for round_number in range(7):
        session.round = round_number
        for side in ["A", "B"]:
            workbook.append({"Session": {"Round": round_number, "Action": "Offer", "Who": side}})
            workbook.update(logger.on_offer(side, bid, round_number / 10, session))
            if interval > 1 and round_number % interval:
                assert workbook.log_rows["Model"][-1] == {}
    # Dense in-memory padding stays aligned even if export compacts one sheet.
    assert len(workbook.log_rows["Session"]) == len(workbook.log_rows["Model"]) == 14
    path = tmp_path / "sessions/A_B_Domain1.xlsx"
    workbook.save(str(path), sparse_sheets={"Model"} if sparse else None)
    assert len(workbook.log_rows["Model"]) == 14

    result = logger.get_estimator_results(tournament(6), ["Model"])

    for round_number in range(7):
        if round_number % interval:
            assert all(values["Model"][round_number] == [] for values in result)
        else:
            assert result[0]["Model"][round_number] == pytest.approx([.1, .4, .1, .4])
            assert result[1]["Model"][round_number] == pytest.approx([.2, .5, .2, .5])
            assert result[2]["Model"][round_number] == pytest.approx([.3, .6, .3, .6])


@pytest.mark.parametrize("layout", ["legacy_dense", "keyed_dense", "keyed_sparse"])
def test_reader_keeps_model_rounds_distinct_and_excludes_acceptance(tmp_path, layout):
    (tmp_path / "sessions").mkdir()
    workbook = ExcelLog(["Session", "First", "Second", "Empty"])
    observations = [(0, "Offer"), (0, "Offer"), (1, "Offer"), (1, "Offer"), (2, "Offer"), (2, "Accept")]
    selected = {"First": {0: 1., 4: 5., 5: 99.}, "Second": {1: 10., 2: 30., 5: 99.}}
    for index, (round_number, action) in enumerate(observations):
        row = {"Session": {"Round": round_number, "Action": action}}
        for name, choices in selected.items():
            if index in choices:
                row[name] = metrics(choices[index])
                if layout != "legacy_dense":
                    row[name].update({"Round": round_number, "Action": action})
        if index == 3:
            row["Second"] = {"OtherLoggerMetric": .7}
        workbook.append(row)
    path = tmp_path / "sessions/A_B_Domain1.xlsx"
    workbook.save(str(path), sparse_sheets={"First", "Second"} if layout == "keyed_sparse" else None)

    rmse, spearman, kendall = EstimatorMetricLogger(str(tmp_path)).get_estimator_results(
        tournament(2), ["First", "Second", "Empty"])

    assert rmse == {"First": [[1., 2.], [], [5., 6.]], "Second": [[10., 11.], [30., 31.], []], "Empty": [[], [], []]}
    assert spearman["First"] == [[3., 4.], [], [7., 8.]]
    assert spearman["Second"] == [[12., 13.], [32., 33.], []]
    assert kendall["First"] == [[5., 6.], [], [9., 10.]]
    assert kendall["Second"] == [[14., 15.], [34., 35.], []]


@pytest.mark.parametrize("missing", ["Round", "Action"])
def test_keyed_measurements_require_complete_keys(tmp_path, missing):
    (tmp_path / "sessions").mkdir()
    workbook = ExcelLog(["Session", "Model"])
    record = {**metrics(.1), "Round": 0, "Action": "Offer"}
    del record[missing]
    workbook.append({"Session": {"Round": 0, "Action": "Offer"}, "Model": record})
    workbook.save(str(tmp_path / "sessions/A_B_Domain1.xlsx"))
    with pytest.raises(ValueError, match="both Round and Action"):
        EstimatorMetricLogger(str(tmp_path)).get_estimator_results(tournament(0), ["Model"])


def test_undefined_rank_values_remain_measurements(session, tmp_path):
    (tmp_path / "sessions").mkdir()
    session.agentA.estimators[0].values = (.2, math.nan, math.nan)
    session.agentB.estimators[0].values = (.4, math.nan, math.nan)
    logger = EstimatorMetricLogger(str(tmp_path), include_round=True)
    workbook = ExcelLog(["Session", "Model"])
    workbook.append({"Session": {"Round": 0, "Action": "Offer"}})
    workbook.update(logger.on_offer("A", session.agentA.preference.bids[0], 0., session))
    workbook.save(str(tmp_path / "sessions/A_B_Domain1.xlsx"))
    rmse, spearman, kendall = logger.get_estimator_results(tournament(0), ["Model"])
    assert rmse["Model"][0] == [.2, .4]
    assert all(math.isnan(value) for value in spearman["Model"][0] + kendall["Model"][0])


def test_replay_supplies_recorded_rounds_and_preserves_final_acceptance(session, tmp_path):
    path = tmp_path / "replay.xlsx"
    workbook = ExcelLog(["Session"])
    bid = session.agentA.preference.bids[0]
    for round_number, action, side in [(4, "Offer", "A"), (4, "Offer", "B"),
                                        (5, "Offer", "A"), (6, "Offer", "B"), (7, "Accept", "A")]:
        workbook.append({"Session": {
            "Round": round_number, "Action": action, "Who": side, "Time": round_number / 10,
            "BidContent": str(bid), "AgentAUtility": 1., "AgentBUtility": 1.,
            "ProductScore": 1., "SocialWelfare": 2.,
        }})
    workbook.save(str(path))
    logger = EstimatorMetricLogger(str(tmp_path), sample_every=2)
    replay = SessionLogs(session.agentA, session.agentB, str(path), [logger])

    final_row = replay.start({"TournamentResults": {}})

    assert replay.round == 7
    assert final_row["Model"]["Round"] == 7
    assert final_row["Model"]["Action"] == "Accept"
    loaded = ExcelLog(file_path=str(path))
    measured = [row for row in loaded.log_rows["Model"] if not math.isnan(row["Round"])]
    assert [row["Round"] for row in measured] == [4, 4, 6]
    # Replay still feeds every offer to the appropriate model; only measurement is sampled.
    assert session.agentA.estimators[0].updates == session.agentB.estimators[0].updates == 2
    assert session.agentA.estimators[0].measurements == session.agentB.estimators[0].measurements == 4


def test_replay_failure_metadata_uses_the_existing_terminal_round(session, tmp_path):
    path = tmp_path / "replay.xlsx"
    workbook = ExcelLog(["Session"])
    bid = session.agentA.preference.bids[0]
    for round_number, side in [(0, "A"), (0, "B"), (1, "A"), (1, "B")]:
        workbook.append({"Session": {"Round": round_number, "Action": "Offer", "Who": side,
                                       "Time": round_number / 10, "BidContent": str(bid)}})
    workbook.save(str(path))
    replay = SessionLogs(session.agentA, session.agentB, str(path),
                         [EstimatorMetricLogger(str(tmp_path), sample_every=3)])
    final_row = replay.start({"TournamentResults": {}})
    assert final_row["TournamentResults"]["Round"] == replay.round == 2
    assert final_row["Model"]["Round"] == 2
    assert final_row["Model"]["Action"] == "Fail"


def replay_workbook(session, path, model_row=None):
    workbook = ExcelLog(["Session", "Model"])
    row = {"Session": {"Round": 0, "Action": "Offer", "Who": "A", "Time": 0.,
                        "BidContent": str(session.agentA.preference.bids[0])}}
    if model_row is not None:
        row["Model"] = model_row
    workbook.append(row)
    workbook.save(str(path))


@pytest.mark.parametrize("options", [{"sample_every": 2}, {"include_round": True}])
def test_keyed_replay_rejects_existing_metrics_without_changing_the_workbook(session, tmp_path, options):
    path = tmp_path / "existing.xlsx"
    replay_workbook(session, path, metrics(0.0))
    original = path.read_bytes()
    logger = EstimatorMetricLogger(str(tmp_path), **options)
    with pytest.raises(ValueError, match="clean copy or a different estimator sheet"):
        SessionLogs(session.agentA, session.agentB, str(path), [logger])
    assert path.read_bytes() == original
    assert session.agentA.estimators[0].updates == session.agentB.estimators[0].updates == 0


def test_default_replay_still_updates_existing_metric_sheets(session, tmp_path):
    path = tmp_path / "existing.xlsx"
    replay_workbook(session, path, metrics(.9))
    replay = SessionLogs(session.agentA, session.agentB, str(path), [EstimatorMetricLogger(str(tmp_path))])
    replay.start({"TournamentResults": {}})
    row = ExcelLog(file_path=str(path)).log_rows["Model"][0]
    assert row["RMSE_A"] == .1
    assert "Round" not in row and "Action" not in row


@pytest.mark.parametrize("model_row", [None, {"OtherLoggerMetric": .8}, {"RMSE_A": math.nan}])
def test_keyed_replay_allows_empty_or_unmeasured_sheets(session, tmp_path, model_row):
    path = tmp_path / "empty.xlsx"
    replay_workbook(session, path, model_row)
    replay = SessionLogs(session.agentA, session.agentB, str(path),
                         [EstimatorMetricLogger(str(tmp_path), sample_every=2)])
    replay.start({"TournamentResults": {}})
    row = ExcelLog(file_path=str(path)).log_rows["Model"][0]
    assert row["RMSE_A"] == .1
    assert row["Round"] == 0
    assert row["Action"] == "Offer"


def test_unkeyed_compacted_history_fails_instead_of_guessing_rounds(tmp_path):
    (tmp_path / "sessions").mkdir()
    workbook = ExcelLog(["Session", "Model"])
    for round_number in range(3):
        workbook.append({"Session": {"Round": round_number, "Action": "Offer"}})
    workbook.log_rows["Model"] = [metrics(.1)]
    workbook.save(str(tmp_path / "sessions/A_B_Domain1.xlsx"))
    with pytest.raises(ValueError, match="Compacted histories require Round and Action"):
        EstimatorMetricLogger(str(tmp_path)).get_estimator_results(tournament(2), ["Model"])


def test_default_dense_history_allows_the_empty_acceptance_row_to_be_trimmed(tmp_path):
    (tmp_path / "sessions").mkdir()
    workbook = ExcelLog(["Session", "Model"])
    workbook.append({"Session": {"Round": 0, "Action": "Offer"}, "Model": metrics(.1)})
    workbook.append({"Session": {"Round": 1, "Action": "Accept"}})
    path = tmp_path / "sessions/A_B_Domain1.xlsx"
    workbook.save(str(path))
    assert len(ExcelLog(file_path=str(path)).log_rows["Model"]) == 1
    rmse, _, _ = EstimatorMetricLogger(str(tmp_path)).get_estimator_results(tournament(1), ["Model"])
    assert rmse["Model"] == [[.1, 1.1], []]
