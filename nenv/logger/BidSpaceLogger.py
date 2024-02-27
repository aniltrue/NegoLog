from nenv.logger.AbstractLogger import AbstractLogger, Bid, SessionLogs, Session, LogRow
from typing import Union, List
from nenv.BidSpace import BidSpace, BidPoint


class BidSpaceLogger(AbstractLogger):
    """
        BidSpaceLogger logs the distances from the Kalai and Nash points in the bid space.
    """
    bidSpace: BidSpace

    def initiate(self):
        self.bidSpace = None

    def before_session_start(self, session: Union[Session, SessionLogs]) -> List[str]:
        """
            Initiate bid space of the domain of the given session.

            :param session: Current negotiation session
            :return: Empty list
        """
        self.bidSpace = BidSpace(session.agentA.preference, session.agentB.preference)

        return []

    def on_offer(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return {"Session": {
            "NashDistance": self.bidSpace.nash_distance(offer),
            "KalaiDistance": self.bidSpace.kalai_distance(offer)
        }}

    def on_accept(self, agent: str, offer: Bid, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return {"TournamentResults": {
            "NashDistance": self.bidSpace.nash_distance(offer),
            "KalaiDistance": self.bidSpace.kalai_distance(offer)
        }}

    def on_fail(self, time: float, session: Union[Session, SessionLogs]) -> LogRow:
        return {"TournamentResults": {
            "NashDistance": self.bidSpace.nash_distance(BidPoint(None, session.agentA.preference.reservation_value, session.agentB.preference.reservation_value)),
            "KalaiDistance": self.bidSpace.kalai_distance(BidPoint(None, session.agentA.preference.reservation_value, session.agentB.preference.reservation_value))
        }}
