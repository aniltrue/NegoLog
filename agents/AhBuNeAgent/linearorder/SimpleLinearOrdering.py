from typing import List

import nenv


class SimpleLinearOrdering:
    """
        This class holds the bid ranking to estimate self preferences
    """
    pref: nenv.Preference   # Real preferences
    bids: List[nenv.Bid]    # Ordered bids

    def __init__(self, pref: nenv.Preference, bids: list):
        """
            Constructor
        :param pref: Preferences of the agent
        :param bids: List of bids (ordered)
        """
        self.pref = pref
        self.bids = bids

    def getMinBid(self) -> nenv.Bid:
        """
            This method provides the bid with minimum utility.
        :return: Minimum bid
        """
        return self.bids[0]

    def getMaxBid(self) -> nenv.Bid:
        """
            This method provides the bid with maximum utility.
        :return: Maximum bid
        """
        return self.bids[-1]

    def getBidByIndex(self, index: int) -> nenv.Bid:
        """
            This method gets the bid at the given index.
        :param index: Index of the bid.
        :return: Bid at the given index
        """
        return self.bids[index]

    def getKnownBidSize(self) -> int:
        """
            This method provides the number of known bids
        :return: Number of known bids
        """
        return len(self.bids)

    def getUtility(self, bid: nenv.Bid) -> int:
        """
            This method returns the index of given bid
        :param bid: Target bid
        :return: Index
        """
        return self.bids.index(bid) + 1

    def contains(self, bid: nenv.Bid) -> bool:
        """
            This method checks if the given bid exists in the bid ranking.
        :param bid: Target bid
        :return: Whether the bid is in the bid ranking, or not
        """
        return bid in self.bids

    def getBids(self):
        """
            This method provides the copy of the bid ranking.
        :return: Copy of the bid list
        """
        return self.bids.copy()

    def with_(self, bid: nenv.Bid, worseBids: list):
        '''
            SimpleLinearOrdering, updated with the given comparison. The bid will be inserted after the first bid that
            is not worse than bid.
        '''
        n = 0

        while n < len(self.bids) and self.bids[n] in worseBids:
            n += 1

        newBids = self.bids.copy()
        newBids.insert(n, bid)

        return SimpleLinearOrdering(self.pref, newBids)
