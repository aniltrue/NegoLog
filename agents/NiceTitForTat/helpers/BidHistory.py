import random
from typing import List, Optional
import nenv


class BidDetails:
    bid: nenv.Bid
    utility: float
    time: float

    def __init__(self, bid: nenv.Bid, utility: float, time: float = 0.):
        self.bid = bid
        self.utility = utility
        self.time = time

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return self.bid.__hash__()


class BidHistory:
    pref: Optional[nenv.Preference]
    history: List[BidDetails]

    def __init__(self, pref: Optional[nenv.Preference] = None, history: Optional[list] = None):
        self.history = history if history is not None else []

        if pref is None:
            self.pref = None
            return

        self.pref = pref

        for bid in pref.bids:
            self.history.append(BidDetails(bid, bid.utility, 0.))

    def filterBetweenTime(self, minT: float, maxT: float):
        return self.filterBetween(0., 1., minT, maxT)

    def filterBetween(self, minU: float, maxU: float, minT: float, maxT: float):
        bidHistory = BidHistory()

        for b in self.history:
            if minU < b.utility <= maxU and minT < b.time <= maxT:
                bidHistory.add(b)

        return bidHistory

    def add(self, b: BidDetails):
        self.history.append(b)

    def getBidDetailsOfUtility(self, u: float) -> BidDetails:
        minDistance = -1
        closestBid = None

        for b in self.history:
            utility = b.utility

            if abs(u - utility) <= minDistance or minDistance == -1:
                minDistance = abs(u - utility)
                closestBid = b

        return closestBid

    def getMaximumUtility(self) -> float:
        max_util = -1

        for b in self.history:
            max_util = max(b.utility, max_util)

        return max_util

    def getMinumumUtility(self) -> float:
        min_util = 1.

        for b in self.history:
            min_util = min(b.utility, min_util)

        return min_util

    def getBestBidDetails(self):
        max_util = -1
        bestBid = None

        for b in self.history:
            if max_util < b.utility:
                max_util = b.utility
                bestBid = b

        return bestBid

    def getBestBidHistory(self, n: int):
        copySortedToUtility = self.getCopySortedToUtility()
        best = BidHistory()

        for i, b in enumerate(copySortedToUtility.history):
            best.add(b)

            if i >= n - 1:
                break

        return best

    def getRandom(self, r: Optional[random.Random] = None) -> Optional[BidDetails]:
        size = len(self.history)

        if size == 0:
            return None

        if r is None:
            return random.choice(self.history)

        return r.choice(self.history)

    def getAverageUtility(self) -> float:
        if len(self.history) == 0:
            return 0.

        total = 0.

        for b in self.history:
            total += b.utility

        return total / len(self.history)

    def getCopySortedToUtility(self):
        copied = BidHistory(None, self.history.copy())

        copied.history = sorted(copied.history, key=lambda b: b.utility, reverse=True)

        return copied
