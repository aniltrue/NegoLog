import json
import pandas as pd
from nenv.logger.AbstractLogger import AbstractLogger, Bid, LogRow, SessionLogs, Session, ExcelLog
from typing import Union
from nenv.utils.Move import *
from nenv.utils.tournament_graphs import draw_heatmap
import numpy as np
import os


class EstimatedMoveLogger(AbstractLogger):
    """
        *EstimatedUtilityLogger* logs estimated move extracted via Estimators. At the end of the tournament, this logger
        measures the performance of the *Estimators* on the move prediction. Move prediction task can be considered as
        a move classification task. Thus, some metrics (e.g., Accuracy, F1) which are commonly used for classification
        tasks are applied for the evaluation. Additionally, this logger also creates a Confusion Matrix for each
        estimator.

        **Note**: It iterates over all *Estimators* of all agents to extract the necessary log.
    """

    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        if len(session.action_history) >= 3:
            for estimator_id in range(len(session.agentA.estimators)):
                current_offer = offer.copy()
                previous_offer = session.action_history[-3].bid

                if agent == 'A':
                    estimated_move_a = get_move(session.agentA.preference.get_utility(previous_offer),
                                                session.agentA.preference.get_utility(current_offer),
                                                session.agentA.estimators[estimator_id].preference.get_utility(
                                                    previous_offer),
                                                session.agentA.estimators[estimator_id].preference.get_utility(
                                                    current_offer))

                    estimated_move_b = get_move(session.agentB.estimators[estimator_id].preference.get_utility(
                        previous_offer),
                        session.agentB.estimators[estimator_id].preference.get_utility(
                            current_offer),
                        session.agentB.preference.get_utility(previous_offer),
                        session.agentB.preference.get_utility(current_offer))

                else:
                    estimated_move_a = get_move(session.agentA.estimators[estimator_id].preference.get_utility(
                        previous_offer),
                        session.agentA.estimators[estimator_id].preference.get_utility(
                            current_offer),
                        session.agentA.preference.get_utility(previous_offer),
                        session.agentA.preference.get_utility(current_offer))

                    estimated_move_b = get_move(session.agentB.preference.get_utility(previous_offer),
                                                session.agentB.preference.get_utility(current_offer),
                                                session.agentB.estimators[estimator_id].preference.get_utility(
                                                    previous_offer),
                                                session.agentB.estimators[estimator_id].preference.get_utility(
                                                    current_offer))

                log = {
                    "EstimatedMoveA": estimated_move_a,
                    "EstimatedMoveB": estimated_move_b,
                }

                row[session.agentA.estimators[estimator_id].name] = log

        return row

    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str], estimator_names: List[str]):
        if len(estimator_names) == 0:
            return

        if not os.path.exists(self.get_path("opponent model/")):
            os.makedirs(self.get_path("opponent model/"))

        moves = self.get_move_list()

        accuracy, confusion_matrices = self.get_accuracy_and_confusion_matrix(tournament_logs, estimator_names)

        tp, fp, fn, recall, precision, f1 = self.calculate(confusion_matrices, estimator_names)

        df = pd.DataFrame(columns=["EstimatorName", "TP", "FP", "FN", "Recall", "Precision", "F1", "Accuracy"])

        for estimator_id in range(len(estimator_names)):
            confusion_matrix_path = "opponent model/%s_move_confusion_matrix" % estimator_names[estimator_id]

            draw_heatmap(confusion_matrices[estimator_id] / (np.sum(confusion_matrices[estimator_id]) + 1e-12), moves,
                         moves, self.get_path(confusion_matrix_path), "Estimated Move", "Real Move")

            df.loc[estimator_id] = {
                "EstimatorName": estimator_names[estimator_id],
                "TP": np.mean(list(tp[estimator_id].values())),
                "FP": np.mean(list(fp[estimator_id].values())),
                "FN": np.mean(list(fn[estimator_id].values())),
                "Recall": np.mean(list(recall[estimator_id].values())),
                "Precision": np.mean(list(precision[estimator_id].values())),
                "F1": np.mean(list(f1[estimator_id].values()))
            }

        df.to_excel(self.get_path("opponent model/estimator_move_performance.xlsx"), sheet_name="Move Classification")

    def get_accuracy_and_confusion_matrix(self, tournament_logs: ExcelLog, estimator_names: List[str]) -> (
                                          List[float], List[np.ndarray]):

        moves = self.get_move_list()

        confusion_matrices = [np.zeros((len(moves), len(moves)), dtype=np.int32) for _ in
                              range(len(estimator_names))]
        accuracy = [0. for _ in range(len(estimator_names))]

        for row in tournament_logs.log_rows["TournamentResults"]:
            agent_a = row["AgentA"]
            agent_b = row["AgentB"]
            domain_name = "Domain%d" % int(row["DomainName"])

            session_path = self.get_path(f"sessions/{agent_a}_{agent_b}_{domain_name}.xlsx")
            session_log = ExcelLog(file_path=session_path)

            for i in range(len(estimator_names)):
                if estimator_names[i] not in session_log.log_rows:
                    break

                for row_index, session_row in enumerate(session_log.log_rows[estimator_names[i]]):
                    real_move = session_log.log_rows["Session"][row_index]["Move"]

                    if real_move == "-" or real_move is None or str(real_move) == "nan":
                        continue

                    estimated_move = session_row["EstimatedMoveA"]

                    confusion_matrices[i][moves.index(real_move)][moves.index(estimated_move)] += 1

                    if real_move == estimated_move:
                        accuracy[i] += 1

                    estimated_move = session_row["EstimatedMoveB"]

                    confusion_matrices[i][moves.index(real_move)][moves.index(estimated_move)] += 1

                    if real_move == estimated_move:
                        accuracy[i] += 1

        for estimator_id in range(len(estimator_names)):
            accuracy[estimator_id] /= np.sum(confusion_matrices[estimator_id])

        return accuracy, confusion_matrices

    def calculate(self, confusion_matrices: List[np.ndarray], estimator_names: List[str]) -> \
            (List[Dict[str, int]], List[Dict[str, int]], List[Dict[str, int]],
             List[Dict[str, float]], List[Dict[str, float]], List[Dict[str, float]]):

        moves = self.get_move_list()

        tp = [{move: 0 for move in moves} for _ in range(len(estimator_names))]
        fp = [{move: 0 for move in moves} for _ in range(len(estimator_names))]
        fn = [{move: 0 for move in moves} for _ in range(len(estimator_names))]

        for estimator_id in range(len(estimator_names)):
            for i in range(confusion_matrices[estimator_id].shape[0]):
                tp[estimator_id][moves[i]] = confusion_matrices[estimator_id][i][i]

                for j in range(confusion_matrices[estimator_id].shape[1]):
                    if i == j:
                        continue

                    fn[estimator_id][moves[i]] += confusion_matrices[estimator_id][i][j]
                    fp[estimator_id][moves[i]] += confusion_matrices[estimator_id][j][i]

        recall = [{move: tp[i][move] / (tp[i][move] + fn[i][move]) for move in moves} for i in
                  range(len(estimator_names))]
        precision = [{move: tp[i][move] / (tp[i][move] + fp[i][move]) for move in moves} for i in
                     range(len(estimator_names))]
        f1 = [{move: 2 * recall[i][move] * precision[i][move] / (recall[i][move] + precision[i][move]) for move in
               moves} for i in range(len(estimator_names))]

        return tp, fp, fn, recall, precision, f1

    @staticmethod
    def get_move_list() -> List[str]:
        return ["Concession", "Fortunate", "Nice", "Selfish", "Silent", "Unfortunate"]
