from typing import List, Optional

import nenv


class OppSimpleLinearOrderding:
    """
        Estimated opponent orderings.
    """
    bids: List[nenv.Bid]  # List of bids where the worst bid is first and the best bid is last.

    def __init__(self):
        """
            Constructor
        """
        self.bids = []

    def getMinBid(self) -> Optional[nenv.Bid]:
        """
            Get the worst bid.
        :return: Worst bid
        """
        if len(self.bids) == 0:
            return None

        return self.bids[0]

    def getMaxBid(self) -> Optional[nenv.Bid]:
        """
            Get the best bid.
        :return: Best bid
        """
        if len(self.bids) == 0:
            return None

        return self.bids[-1]

    def getBidByIndex(self, index: int) -> nenv.Bid:
        """
            Get the bid with index.
        :param index: Index in the order
        :return: Corresponding bid
        """
        return self.bids[index]

    def getKnownBidSize(self) -> int:
        """
            Get number of known bids
        :return: Number of known bids
        """
        return len(self.bids)

    def getUtility(self, bid: nenv.Bid) -> int:
        """
            Get the index of the given bid if it exists. Otherwise, return 0.
        :param bid: Target bid
        :return: Index in the ordered bids.
        """
        if bid not in self.bids:
            return 0

        return self.bids.index(bid) + 1

    def contains(self, bid: nenv.Bid) -> bool:
        """
            Check if the given bid is in the ordered bid list
        :param bid: Target bid
        :return: Whether the given bid is in the ordered bid list
        """
        return bid in self.bids

    def getBids(self) -> list:
        """
            Get the ordered bid list.
        :return: List of bids
        """
        return self.bids.copy()

    def isAvailable(self) -> bool:
        """
            Check if the number of known bids >= 6
        :return: Whether the number of known bids >= 6
        """
        return len(self.bids) >= 6

    def updateBid(self, bid: nenv.Bid):
        """
            This method is called when a bid is received from the opponent.
        :param bid: Received bid
        :return: Nothing
        """
        if bid not in self.bids:
            # Assume that the opponent make a concession move
            self.bids.insert(0, bid.copy())
