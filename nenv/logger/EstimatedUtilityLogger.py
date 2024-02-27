import pandas as pd
from nenv.logger.AbstractLogger import AbstractLogger, Bid, LogRow, SessionLogs, Session, ExcelLog
from typing import Union
from nenv.utils.Move import *
import os


class EstimatedUtilityLogger(AbstractLogger):
    """
        *EstimatedUtilityLogger* logs some estimated utility-based information extracted via Estimators,
        as listed below:

        - Estimated Opponent Utility.
        - Estimated Product Score
        - Estimated Social Welfare

        **Note**: It iterates over all *Estimators* of all agents to extract the necessary log.
    """

    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        for estimator_id in range(len(session.agentA.estimators)):
            agentA_utility = session.agentA.preference.get_utility(offer)
            agentB_utility = session.agentB.preference.get_utility(offer)

            estimated_utility_B = session.agentB.estimators[estimator_id].preference.get_utility(offer)
            estimated_utility_A = session.agentA.estimators[estimator_id].preference.get_utility(offer)

            log = {
                "EstimatedOpponentUtilityA": estimated_utility_B,
                "EstimatedOpponentUtilityB": estimated_utility_A,
                "EstimatedProductScoreA": agentA_utility * estimated_utility_B,
                "EstimatedProductScoreB": agentB_utility * estimated_utility_A,
                "EstimatedSocialWelfareA": agentA_utility + estimated_utility_B,
                "EstimatedSocialWelfareB": agentB_utility + estimated_utility_A,
            }

            row[session.agentA.estimators[estimator_id].name] = log

        return row

    def on_accept(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        for estimator_id in range(len(session.agentA.estimators)):
            estimated_preference_A = session.agentA.estimators[estimator_id].preference

            log = {
                "EstimatedProductScoreA": session.agentA.preference.get_utility(
                    offer) * estimated_preference_A.get_utility(offer),
                "EstimatedSocialWelfareA": session.agentA.preference.get_utility(
                    offer) + estimated_preference_A.get_utility(offer)
            }

            estimated_preference_B = session.agentB.estimators[estimator_id].preference

            log.update({
                "EstimatedProductScoreB": session.agentB.preference.get_utility(
                    offer) * estimated_preference_B.get_utility(offer),
                "EstimatedSocialWelfareB": session.agentB.preference.get_utility(
                    offer) + estimated_preference_B.get_utility(offer)
            })

            row[session.agentA.estimators[estimator_id].name] = log

        return row

    def on_fail(self, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        for estimator_id in range(len(session.agentA.estimators)):
            log = {
                "EstimatedProductScoreA": 0,
                "EstimatedSocialWelfareA": session.agentA.preference.reservation_value
            }

            log.update({
                "EstimatedProductScoreB": 0,
                "EstimatedSocialWelfareB": session.agentB.preference.reservation_value
            })

            row[session.agentA.estimators[estimator_id].name] = log

        return row

    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str], estimator_names: List[str]):
        if len(estimator_names) == 0:
            return

        if not os.path.exists(self.get_path("opponent model/")):
            os.makedirs(self.get_path("opponent model/"))

        self.extract_estimator_names(estimator_names)

    def extract_estimator_names(self, names: List[str]):
        pd.DataFrame(names).to_excel(self.get_path("opponent model/estimator_names.xlsx"), sheet_name="EstimatorNames")
