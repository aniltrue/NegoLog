import math
import nenv
from agents.Kawaii.NegotiatingInfo import NegotiatingInfo


class Strategy:
    pref: nenv.Preference
    negotiatingInfo: NegotiatingInfo
    minThreshold: float
    df: float
    rv: float

    def __init__(self, pref: nenv.Preference, negotiatingInfo: NegotiatingInfo):
        self.pref = pref
        self.negotiatingInfo = negotiatingInfo
        self.df = 1.
        self.minThreshold = 0.8
        self.rv = self.pref.reservation_value

    def selectAccept(self, offeredBid: nenv.Bid, time: float):
        offeredBidUtil = self.pref.get_utility(offeredBid)

        return offeredBidUtil >= self.getThreshold(time)

    def getThreshold(self, time: float):
        a = self.minThreshold

        threshold = 1. - (1 - a) * math.pow(time, (1. / 0.5))

        opponents = self.negotiatingInfo.opponents

        acceptNum = 0

        for sender in opponents:
            if self.negotiatingInfo.getOpponentsBool(sender):
                acceptNum += 1

        negotiatorNum = self.negotiatingInfo.negotiatorNum - 1

        threshold -= (threshold - self.minThreshold) * (acceptNum / negotiatorNum)

        self.negotiatingInfo.opponentsBool = {}

        threshold = threshold * math.pow(self.df, time)

        if threshold < self.minThreshold:
            threshold = self.minThreshold

        return threshold
