from typing import List, Optional
import nenv


class OwnBidHistory:
    BidHistory: List[nenv.Bid]
    minBidInHistory: Optional[nenv.Bid]

    def __init__(self):
        self.BidHistory = []
        self.minBidInHistory = None

    def addBid(self, bid: nenv.Bid, pref: nenv.Preference):
        if bid not in self.BidHistory:
            self.BidHistory.append(bid)

        if len(self.BidHistory) == 1:
            self.minBidInHistory = self.BidHistory[0]
        else:
            if pref.get_utility(bid) < pref.get_utility(self.minBidInHistory):
                self.minBidInHistory = bid

    def chooseLowestBidInHistory(self, pref: nenv.Preference):
        minUtility = 100
        minBid = None

        for bid in self.BidHistory:
            if pref.get_utility(bid) < minUtility:
                minUtility = pref.get_utility(bid)
                minBid = bid

        return minBid
