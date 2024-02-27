import numpy as np
from nenv.logger.AbstractLogger import AbstractLogger, Bid, SessionLogs, Session, LogRow
from typing import Union
from nenv.BidSpace import BidSpace, BidPoint


class EstimatedBidSpaceLogger(AbstractLogger):
    """
        EstimatedBidSpaceLogger logs the distances from the Kalai and Nash points in the estimated bid space.
        It iterates over all provided Estimators of the agents to generate the estimated bid space.
        Then, it logs the estimated Kalai and Nash distances for each Estimator of each agent.
    """

    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        for estimator_id in range(len(session.agentA.estimators)):
            estimated_bid_space_A = BidSpace(session.agentA.preference, session.agentA.estimators[estimator_id].preference)
            estimated_bid_space_B = BidSpace(session.agentB.estimators[estimator_id].preference, session.agentB.preference)

            agentA_utility = session.agentA.preference.get_utility(offer)
            agentB_utility = session.agentB.preference.get_utility(offer)

            estimated_opponent_utilityA = session.agentB.estimators[estimator_id].preference.get_utility(offer)
            estimated_opponent_utilityB = session.agentA.estimators[estimator_id].preference.get_utility(offer)

            log = {
                "EstimatedNashDistanceA": estimated_bid_space_A.nash_distance(
                    BidPoint(offer, agentA_utility, estimated_opponent_utilityA)),
                "EstimatedNashDistanceB": estimated_bid_space_B.nash_distance(
                    BidPoint(offer, estimated_opponent_utilityB, agentB_utility)),
                "EstimatedKalaiDistanceA": estimated_bid_space_A.kalai_distance(
                    BidPoint(offer, agentA_utility, estimated_opponent_utilityA)),
                "EstimatedKalaiDistanceB": estimated_bid_space_B.kalai_distance(
                    BidPoint(offer, estimated_opponent_utilityB, agentB_utility)),
            }

            row[session.agentA.estimators[estimator_id].name] = log

        return row

    def on_session_end(self, final_row: LogRow, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        for estimator in session.agentA.estimators:
            estimator_results = session.session_log.to_data_frame(estimator.name)
            estimator_results.dropna(inplace=True)

            log = {
                "EstimatedNashDistanceA": np.mean(estimator_results["EstimatedNashDistanceA"].to_list()) if len(estimator_results) > 0 else 0.,
                "EstimatedNashDistanceB": np.mean(estimator_results["EstimatedNashDistanceB"].to_list()) if len(estimator_results) > 0 else 0.,
                "EstimatedKalaiDistanceA": np.mean(estimator_results["EstimatedKalaiDistanceA"].to_list()) if len(estimator_results) > 0 else 0.,
                "EstimatedKalaiDistanceB": np.mean(estimator_results["EstimatedKalaiDistanceB"].to_list()) if len(estimator_results) > 0 else 0.,
            }

            log["EstimatedNashDistance"] = (log["EstimatedNashDistanceA"] + log["EstimatedNashDistanceB"]) / 2.
            log["EstimatedKalaiDistance"] = (log["EstimatedKalaiDistanceA"] + log["EstimatedKalaiDistanceB"]) / 2.

            row[estimator.name] = log

        return row
