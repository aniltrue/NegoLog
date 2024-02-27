from nenv.logger.AbstractLogger import AbstractLogger, Bid, SessionLogs, Session, LogRow, ExcelLog
from typing import Union
import os
from nenv.Agent import AbstractAgent
from typing import List
import numpy as np
import pandas as pd


class EstimatorOnlyFinalMetricLogger(AbstractLogger):
    """
        EstimatorOnlyFinalMetricLogger is a cheaper (in terms of computational time) version of EstimatorMetricLogger.
        It logs *RMSE*, *Kendall-Tau* and *Spearman* results of all Estimators only when the session ends instead of
        round by round. Therefore, it cannot plot metric results round by round.
    """

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
            RMSE, spearman, kendall = [], [], []
            results = tournament_logs.to_data_frame(estimator_names[i])

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
