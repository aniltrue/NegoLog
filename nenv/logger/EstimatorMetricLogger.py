from nenv.logger.AbstractLogger import AbstractLogger, Bid, SessionLogs, Session, LogRow, ExcelLog
from typing import Union
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

    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return self.get_metrics(session.agentA, session.agentB)

    def on_accept(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return self.get_metrics(session.agentA, session.agentB)

    def on_fail(self, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return self.get_metrics(session.agentA, session.agentB)

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
        tournament_results = tournament_logs.to_data_frame()

        max_round = max(tournament_results["TournamentResults"]["Round"].to_list())

        rmse = {name: [[] for _ in range(max_round + 1)] for name in estimator_names}
        spearman = {name: [[] for _ in range(max_round + 1)] for name in estimator_names}
        kendall = {name: [[] for _ in range(max_round + 1)] for name in estimator_names}

        for _, row in tournament_results["TournamentResults"].to_dict('index').items():
            agent_a = row["AgentA"]
            agent_b = row["AgentB"]
            domain_name = "Domain%d" % int(row["DomainName"])

            session_path = self.get_path(f"sessions/{agent_a}_{agent_b}_{domain_name}.xlsx")

            for i in range(len(estimator_names)):
                session_log = ExcelLog(file_path=session_path)

                for row_index, estimator_row in enumerate(session_log.log_rows[estimator_names[i]]):
                    if session_log.log_rows["Session"][row_index]["Action"] == "Accept":
                        break

                    _round = session_log.log_rows["Session"][row_index]["Round"]

                    rmse[estimator_names[0]][_round].append(estimator_row["RMSE_A"])
                    spearman[estimator_names[0]][_round].append(estimator_row["SpearmanA"])
                    kendall[estimator_names[0]][_round].append(estimator_row["KendallTauA"])
                    rmse[estimator_names[0]][_round].append(estimator_row["RMSE_B"])
                    spearman[estimator_names[0]][_round].append(estimator_row["SpearmanB"])
                    kendall[estimator_names[0]][_round].append(estimator_row["KendallTauB"])

        return rmse, spearman, kendall

    def draw(self, rmse: dict, spearman: dict, kendall: dict):
        rmse_mean, _ = self.get_mean_std(rmse)
        spearman_mean, _ = self.get_mean_std(spearman)
        kendall_mean, _ = self.get_mean_std(kendall)

        draw_line(rmse_mean, self.get_path("opponent model/estimator_rmse"), "Rounds", "RMSE")
        draw_line(spearman_mean, self.get_path("opponent model/estimator_spearman"), "Rounds", "Spearman")
        draw_line(kendall_mean, self.get_path("opponent model/estimator_kendall_tau"), "Rounds", "KendallTau")

        # After median round, these metrics may mislead since the number of session dramatically decreases.
        median_round = self.get_median_round(rmse)

        for estimator_name in rmse:
            rmse[estimator_name] = rmse[estimator_name][:median_round]
            spearman[estimator_name] = spearman[estimator_name][:median_round]
            kendall[estimator_name] = kendall[estimator_name][:median_round]

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

        return round(float(np.median(counts)))

    @staticmethod
    def get_mean_std(results: dict) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
        means, std = {}, {}

        for estimator_name, rounds in results.items():
            means[estimator_name] = []
            std[estimator_name] = []

            for result in rounds:
                means[estimator_name].append(float(np.mean(result)))
                std[estimator_name].append(float(np.std(result)))

        return means, std
