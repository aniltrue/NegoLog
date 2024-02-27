from nenv.logger.AbstractLogger import AbstractLogger, Bid, SessionLogs, Session, LogRow
from typing import Union
from nenv.utils.Move import *
import pandas as pd


class MoveAnalyzeLogger(AbstractLogger):
    """
        MoveAnalyzeLogger logs some move analysis at the end of each negotiation session. These analysis are listed
        below. These analysis are applied for each agent.

        - Behavior Sensitivity
        - Awareness
        - Move Correlation
    """
    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return {"Session": {"Move": self._get_move(session, agent)}}

    def on_session_end(self, final_row: LogRow, session: Union[Session, SessionLogs]) -> LogRow:
        row = {}

        if len(session.session_log.log_rows["Session"]) == 0:
            return {"MoveAnalyze": {}}

        movement_analyse_a = self.analyze_moves("A", session)
        movement_analyse_b = self.analyze_moves("B", session)

        for key, value in movement_analyse_a.items():
            row["%sA" % key] = value

        for key, value in movement_analyse_b.items():
            row["%sB" % key] = value

        return {"MoveAnalyze": row}

    def analyze_moves(self, agent: str, session: Session) -> dict:
        opponent = "A" if agent == "B" else "B"

        session_log = pd.DataFrame(session.session_log.log_rows["Session"])

        move_self = session_log.loc[(session_log["Who"] == agent) & (session_log["Move"] != "-") & (session_log["Move"] != None), "Move"].to_list()
        move_opp = session_log.loc[(session_log["Who"] == opponent) & (session_log["Move"] != "-") & (session_log["Move"] != None), "Move"].to_list()

        analyze = {
            "BehaviorSensitivity": calculate_behavior_sensitivity(move_self),
            "Awareness": calculate_awareness(move_self, move_opp),
            "MoveCorrelation": calculate_move_correlation(move_self, move_opp)
        }

        analyze.update(get_move_distribution(move_self))

        return analyze

    def _get_move(self, session: Session, agent_no: str) -> str:
        if len(session.action_history) < 3:
            return "-"

        if agent_no == "A":
            offered_utility = session.agentA.preference.get_utility(session.action_history[-1].bid)
            prev_offered_utility = session.agentA.preference.get_utility(session.action_history[-3].bid)

            opponent_utility = session.agentB.preference.get_utility(session.action_history[-1].bid)
            prev_opponent_utility = session.agentB.preference.get_utility(session.action_history[-3].bid)
        else:
            offered_utility = session.agentB.preference.get_utility(session.action_history[-1].bid)
            prev_offered_utility = session.agentB.preference.get_utility(session.action_history[-3].bid)

            opponent_utility = session.agentA.preference.get_utility(session.action_history[-1].bid)
            prev_opponent_utility = session.agentA.preference.get_utility(session.action_history[-3].bid)

        return get_move(prev_offered_utility, offered_utility, prev_opponent_utility, opponent_utility)
