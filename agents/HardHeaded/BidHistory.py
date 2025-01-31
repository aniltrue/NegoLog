from typing import Tuple, List, Optional
import nenv


class BidHistory:
    """
        This class holds the offered bids of both the agent and opponent.
    """
    myBids: List[Tuple[float, nenv.Bid]]    # Agent history
    opponentBids: List[nenv.Bid]            # Opponent history
    pref: nenv.Preference                   # Preferences

    def __init__(self, pref: nenv.Preference):
        """
            Constructor
        :param pref: Preferences of the agent
        """
        self.pref = pref
        self.myBids = []
        self.opponentBids = []

    def getOpponentSecondLastBid(self) -> Optional[nenv.Bid]:
        """
            This method returns the second last bid of the opponent if it exists.
        :return: Second last bid of the opponent
        """
        if len(self.opponentBids) > 1:
            return self.opponentBids[-2]

        return None

    def getOpponentLastBid(self) -> Optional[nenv.Bid]:
        """
            This method returns the last bid of the opponent if it exists.
        :return: Last bid of the opponent
        """
        if len(self.opponentBids) > 0:
            return self.opponentBids[-1]

        return None

    def BidDifference(self, first: nenv.Bid, second: nenv.Bid) -> dict:
        """
            This method compares two given bid issue-by-issue, and returns the issue difference.
        :param first: First bid
        :param second: Second bid
        :return: Different issues
        """
        diff = {}

        for issue in self.pref.issues:
            if first[issue] == second[issue]:
                diff[issue] = 0
            else:
                diff[issue] = 1

        return diff

    def BidDifferenceofOpponentsLastTwo(self) -> dict:
        """
            This method returns the issue difference between the last two received bids
        :return: Issue difference
        """
        return self.BidDifference(self.getOpponentLastBid(), self.getOpponentSecondLastBid())
