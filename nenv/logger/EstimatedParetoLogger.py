import os

import numpy as np

from nenv.BidSpace import BidSpace, BidPoint
from nenv.logger.AbstractLogger import AbstractLogger, Session, SessionLogs, Bid, LogRow
from typing import List, Union, Optional

from nenv.utils import ExcelLog


class EstimatedParetoLogger(AbstractLogger):
    """
        *EstimatedParetoLogger* evaluate the pareto frontier estimation performance of opponent models as a binary
        classification task.

        **Note**: It iterates over all *Estimators* of all agents to extract the necessary log.

        **Note**: This logger increases the computational time due to the expensive process of the pareto estimation.
    """

    real_pareto: Optional[List[BidPoint]]

    def before_session_start(self, session: Union[Session, SessionLogs]) -> List[str]:
        if len(session.agentA.estimators) == 0:
            return []

        self.real_pareto = BidSpace(session.agentA.preference, session.agentB.preference).pareto

        return []

    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        if len(session.agentA.estimators) == 0:
            return {}

        row = {}

        for estimator_id in range(len(session.agentA.estimators)):
            pareto_a = BidSpace(session.agentA.preference, session.agentA.estimators[estimator_id].preference).pareto
            pareto_b = BidSpace(session.agentB.estimators[estimator_id].preference, session.agentB.preference).pareto

            precision_a, recall_a, f1_a = self.calculate_error(pareto_a)
            precision_b, recall_b, f1_b = self.calculate_error(pareto_b)

            row[session.agentA.estimators[estimator_id].name] = {
                "PrecisionA": precision_a,
                "RecallA": recall_a,
                "F1A": f1_a,
                "PrecisionB": precision_b,
                "RecallB": recall_b,
                "F1B": f1_b,
            }

        return row

    def on_session_end(self, final_row: LogRow, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        for estimator in session.agentA.estimators:
            estimator_results = session.session_log.to_data_frame(estimator.name)
            estimator_results.dropna(inplace=True)

            row[estimator.name] = {
                "PrecisionA": np.mean(estimator_results["PrecisionA"].to_list()) if len(
                    estimator_results) > 0 else 0.,
                "RecallA": np.mean(estimator_results["RecallA"].to_list()) if len(
                    estimator_results) > 0 else 0.,
                "F1A": np.mean(estimator_results["F1A"].to_list()) if len(
                    estimator_results) > 0 else 0.,
                "PrecisionB": np.mean(estimator_results["PrecisionB"].to_list()) if len(
                    estimator_results) > 0 else 0.,
                "RecallB": np.mean(estimator_results["RecallB"].to_list()) if len(
                    estimator_results) > 0 else 0.,
                "F1B": np.mean(estimator_results["F1B"].to_list()) if len(
                    estimator_results) > 0 else 0.,
            }

        return row

    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str],
                          estimator_names: List[str]):
        if len(estimator_names) == 0:
            return

        if not os.path.exists(self.get_path("opponent model/")):
            os.makedirs(self.get_path("opponent model/"))

        with open(self.get_path("opponent model/pareto_estimation_results.csv"), "w") as f:
            f.write("Name;Precision;Recall;F1;\n")
            for estimator_name in estimator_names:
                count = 0
                total_precision, total_recall, total_f1 = 0., 0., 0.

                for row in tournament_logs.log_rows[estimator_name]:
                    total_precision += row["PrecisionA"] + row["PrecisionB"]
                    total_recall += row["RecallA"] + row["RecallB"]
                    total_f1 += row["F1A"] + row["F1B"]
                    count += 2

                f.write(f"{estimator_name};{total_precision / count};{total_recall / count};{total_f1 / count};\n")

    def calculate_error(self, estimated_pareto: List[BidPoint]) -> (float, float, float):
        tp, fp, fn = 0., 0., 0.

        for bid_point in estimated_pareto:
            if bid_point in self.real_pareto:
                tp += 1.
            else:
                fp += 1.

        for bid_point in self.real_pareto:
            if bid_point not in estimated_pareto:
                fn += 1.

        recall = tp / (tp + fp)
        precision = tp / (tp + fn)
        f1 = 2 * precision * recall / (precision + recall)

        return precision, recall, f1
