from nenv.logger.AbstractLogger import AbstractLogger, Bid, SessionLogs, Session, LogRow, ExcelLog
from typing import Union
from numbers import Integral
import os
from nenv.Agent import AbstractAgent
from nenv.utils.tournament_graphs import draw_line
from typing import List, Tuple, Dict
import numpy as np
import pandas as pd


class EstimatorMetricLogger(AbstractLogger):
    """
        EstimatorMetricLogger logs the performance analysis of each Estimator round by round. RMSE, Spearman and
        Kendal-Tau metrics which are commonly used for the evaluation of an Opponent Model are applied
        [Baarslag2013]_ [Keskin2023]_

        At the end of tournament, it generates overall results containing these metric results. It also draws the
        necessary plots.

        **Note**: This logger increases the computational time due to the expensive calculation of the metrics. If you
        have strict time for the tournament run, you can look *EstimatorOnlyFinalMetricLogger* which is a cheaper
        version of this logger.

        .. [Baarslag2013] Tim Baarslag, Mark J.C. Hendrikx, Koen V. Hindriks, and Catholijn M. Jonker. Predicting the performance of opponent models in automated negotiation. In International Joint Conferences on Web Intelligence (WI) and Intelligent Agent Technologies (IAT), 2013 IEEE/WIC/ACM, volume 2, pages 59–66, 2013.
        .. [Keskin2023] Mehmet Onur Keskin, Berk Buzcu, and Reyhan Aydoğan. Conflict-based negotiation strategy for human-agent negotiation. Applied Intelligence, 53(24):29741–29757, dec 2023.

    """

    _metric_columns = ("RMSE_A", "RMSE_B", "SpearmanA", "SpearmanB", "KendallTauA", "KendallTauB",
                       "RMSE", "Spearman", "KendallTau")

    def __init__(self, log_dir: str, sample_every: int = 1, include_round: bool = False):
        """Configure optional round sampling without changing model updates.

        ``sample_every=1`` measures every offer, preserving the existing columns.
        Larger intervals measure both sides' offers in rounds 0, N, 2N, ... and
        automatically include ``Round`` and ``Action`` keys. ``include_round``
        can add these keys without sampling. Acceptance and failure callbacks
        always measure the final model state, regardless of the interval.
        """
        if isinstance(sample_every, bool) or not isinstance(sample_every, Integral) or sample_every < 1:
            raise ValueError("sample_every must be a positive integer")
        if not isinstance(include_round, bool):
            raise ValueError("include_round must be a bool")
        self.sample_every = int(sample_every)
        self.include_round = include_round or self.sample_every > 1
        super().__init__(log_dir)

    def before_session_start(self, session: Union[Session, SessionLogs]) -> List[str]:
        if self.include_round and isinstance(session, SessionLogs):
            # Replay merges rows. Refuse to mix new sampled measurements with
            # old measurements that skipped callbacks would leave untouched.
            existing = ExcelLog(file_path=session.log_path)
            for estimator in session.agentA.estimators:
                if any(pd.notna(values.get(column))
                       for values in existing.log_rows.get(estimator.name, [])
                       for column in self._metric_columns):
                    raise ValueError(
                        "Round-keyed metric replay found existing measurements in %r. "
                        "Use a clean copy or a different estimator sheet name." % estimator.name
                    )
        return []

    def _with_round(self, metrics: LogRow, session: Union[Session, SessionLogs], action: str) -> LogRow:
        if self.include_round:
            for values in metrics.values():
                values.update({"Round": int(session.round), "Action": action})
        return metrics

    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        if self.sample_every > 1 and session.round % self.sample_every != 0:
            return {}
        return self._with_round(self.get_metrics(session.agentA, session.agentB), session, "Offer")

    def on_accept(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return self._with_round(self.get_metrics(session.agentA, session.agentB), session, "Accept")

    def on_fail(self, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return self._with_round(self.get_metrics(session.agentA, session.agentB), session, "Fail")

    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str], estimator_names: List[str]):
        if len(estimator_names) == 0:
            return

        if not os.path.exists(self.get_path("opponent model/")):
            os.makedirs(self.get_path("opponent model/"))

        self.extract_estimator_summary(tournament_logs, estimator_names)
        rmse, kendall, spearman = self.get_estimator_results(tournament_logs, estimator_names)

        self.draw(rmse, kendall, spearman)

    def get_metrics(self, agent_a: AbstractAgent, agent_b: AbstractAgent) -> LogRow:
        row = {}

        for estimator_id in range(len(agent_a.estimators)):
            rmseA, spearmanA, kendallA = agent_a.estimators[estimator_id].calculate_error(agent_b.preference)
            rmseB, spearmanB, kendallB = agent_b.estimators[estimator_id].calculate_error(agent_a.preference)

            log = {
                "RMSE_A": rmseA,
                "RMSE_B": rmseB,
                "SpearmanA": spearmanA,
                "SpearmanB": spearmanB,
                "KendallTauA": kendallA,
                "KendallTauB": kendallB,
                "RMSE": (rmseA + rmseB) / 2.,
                "Spearman": (spearmanA + spearmanB) / 2.,
                "KendallTau": (kendallA + kendallB) / 2.
            }

            row[agent_a.estimators[estimator_id].name] = log

        return row

    def extract_estimator_summary(self, tournament_logs: ExcelLog, estimator_names: List[str]):
        summary = pd.DataFrame(
            columns=["EstimatorName", "Avg.RMSE", "Std.RMSE", "Avg.Spearman", "Std.Spearman", "Avg.KendallTau",
                     "Std.KendallTau"]
        )

        for i in range(len(estimator_names)):
            results = tournament_logs.to_data_frame(estimator_names[i])

            RMSE, spearman, kendall = [], [], []

            RMSE.extend(results["RMSE_A"].to_list())
            RMSE.extend(results["RMSE_B"].to_list())

            spearman.extend(results["SpearmanA"].to_list())
            spearman.extend(results["SpearmanB"].to_list())

            kendall.extend(results["KendallTauA"].to_list())
            kendall.extend(results["KendallTauB"].to_list())

            summary.loc[i] = {
                "EstimatorName": estimator_names[i],
                "Avg.RMSE": np.mean(RMSE),
                "Std.RMSE": np.std(RMSE),
                "Avg.Spearman": np.mean(spearman),
                "Std.Spearman": np.std(spearman),
                "Avg.KendallTau": np.mean(kendall),
                "Std.KendallTau": np.std(kendall)
            }

        summary.sort_values(by="Avg.RMSE", inplace=True, ascending=True)

        summary.to_excel(self.get_path("opponent model/estimator_summary.xlsx"), sheet_name="EstimatorSummary")

    def get_estimator_results(self, tournament_logs: ExcelLog, estimator_names: list) -> Tuple[Dict[str, List[List[float]]], Dict[str, List[List[float]]], Dict[str, List[List[float]]]]:
        """Read metric histories, using explicit keys when available.

        Old sheets without ``Round`` are read by their dense row alignment with
        ``Session``. Sampled sheets may keep that padding or omit it when saved:
        their measurement rows must retain both ``Round`` and ``Action``.
        An unkeyed row-count mismatch is rejected because its original rounds
        cannot be recovered reliably. A trailing empty acceptance row may be
        absent from legacy metric sheets, as in the default workbook output.
        Empty padding and rows belonging only to other loggers are ignored.
        Acceptance rows remain excluded from the per-round curves.
        """
        tournament_results = tournament_logs.to_data_frame()

        max_round = int(max(tournament_results["TournamentResults"]["Round"].to_list()))

        rmse = {name: [[] for _ in range(max_round + 1)] for name in estimator_names}
        spearman = {name: [[] for _ in range(max_round + 1)] for name in estimator_names}
        kendall = {name: [[] for _ in range(max_round + 1)] for name in estimator_names}

        for _, row in tournament_results["TournamentResults"].to_dict('index').items():
            session_path = self.get_session_path(row)

            session_log = ExcelLog(file_path=session_path)
            session_rows = session_log.log_rows["Session"]
            metric_columns = self._metric_columns[:6]
            before_accept = next((index for index, values in enumerate(session_rows)
                                  if values.get("Action") == "Accept"), len(session_rows))

            for estimator_name in estimator_names:
                estimator_rows = session_log.log_rows.get(estimator_name, [])
                keyed = any(pd.notna(values.get("Round")) or pd.notna(values.get("Action"))
                            for values in estimator_rows)
                if (not keyed and len(estimator_rows) not in {len(session_rows), before_accept}
                        and any(pd.notna(values.get(column)) for values in estimator_rows for column in metric_columns)):
                    raise ValueError(
                        "Unkeyed metric sheet %r does not match the dense Session row count. "
                        "Compacted histories require Round and Action keys." % estimator_name
                    )

                for row_index, estimator_row in enumerate(estimator_rows):
                    action = (estimator_row.get("Action") if keyed
                              else session_rows[row_index]["Action"])
                    if action == "Accept":
                        break
                    if not any(pd.notna(estimator_row.get(column)) for column in metric_columns):
                        continue

                    if keyed:
                        round_value = estimator_row.get("Round")
                        if pd.isna(round_value) or pd.isna(action):
                            raise ValueError("Keyed metric rows must contain both Round and Action")
                    else:
                        round_value = session_rows[row_index]["Round"]

                    _round = int(round_value)
                    if _round != round_value or not 0 <= _round <= max_round:
                        raise ValueError("Metric Round must be an integer within the tournament round range")

                    rmse[estimator_name][_round].extend([estimator_row.get("RMSE_A", np.nan), estimator_row.get("RMSE_B", np.nan)])
                    spearman[estimator_name][_round].extend([estimator_row.get("SpearmanA", np.nan), estimator_row.get("SpearmanB", np.nan)])
                    kendall[estimator_name][_round].extend([estimator_row.get("KendallTauA", np.nan), estimator_row.get("KendallTauB", np.nan)])

        return rmse, spearman, kendall

    def draw(self, rmse: dict, spearman: dict, kendall: dict):
        if not any(values for rounds in rmse.values() for values in rounds):
            return  # No offers were measured, so there is no curve to plot.
        rmse_mean, _ = self.get_mean_std(rmse)
        spearman_mean, _ = self.get_mean_std(spearman)
        kendall_mean, _ = self.get_mean_std(kendall)

        draw_line(rmse_mean, self.get_path("opponent model/estimator_rmse"), "Rounds", "RMSE")
        draw_line(spearman_mean, self.get_path("opponent model/estimator_spearman"), "Rounds", "Spearman")
        draw_line(kendall_mean, self.get_path("opponent model/estimator_kendall_tau"), "Rounds", "KendallTau")

        # After median round, these metrics may mislead since the number of session dramatically decreases.
        median_round = self.get_median_round(rmse)

        # Slice the plotted means without modifying the caller's observations.
        rmse_mean = {name: values[:median_round] for name, values in rmse_mean.items()}
        spearman_mean = {name: values[:median_round] for name, values in spearman_mean.items()}
        kendall_mean = {name: values[:median_round] for name, values in kendall_mean.items()}

        draw_line(rmse_mean, self.get_path("opponent model/estimator_rmse_until_median_round"), "Rounds", "RMSE")
        draw_line(spearman_mean, self.get_path("opponent model/estimator_spearman_until_median_round"), "Rounds",
                  "Spearman")
        draw_line(kendall_mean, self.get_path("opponent model/estimator_kendall_tau_until_median_round"), "Rounds",
                  "KendallTau")

    @staticmethod
    def get_median_round(results: dict) -> int:
        counts = []

        for estimator_name, rounds in results.items():
            for i, results in enumerate(rounds):
                for j in range(len(results)):
                    counts.append(i)

            break

        return round(float(np.median(counts))) if counts else 0

    @staticmethod
    def get_mean_std(results: dict) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
        means, std = {}, {}

        for estimator_name, rounds in results.items():
            means[estimator_name] = []
            std[estimator_name] = []

            for result in rounds:
                means[estimator_name].append(float(np.mean(result)) if result else np.nan)
                std[estimator_name].append(float(np.std(result)) if result else np.nan)

        return means, std
