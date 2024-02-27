import math

import nenv
from agents.AgentKN.etc.negotiatingInfo import negotiatingInfo


class strategy:
    pref: nenv.Preference
    negotiatingInfo: negotiatingInfo

    rv: float

    def __init__(self, pref: nenv.Preference, negotiatingInfo):
        self.pref = pref
        self.negotiatingInfo = negotiatingInfo

        self.rv = self.pref.reservation_value

    def selectAccept(self, offeredBid: nenv.Bid, time: float):
        offeredBidUtil = self.pref.get_utility(offeredBid)

        if offeredBidUtil >= self.getThreshold(time):
            return True

        return False

    def selectEndNegotiation(self, time: float):
        return False

    def getThreshold(self, time: float) -> float:
        threshold = 1.0

        mi = 0.
        ave = 0.
        extra = 0.

        opponents = self.negotiatingInfo.opponents

        sd = 0.

        for sender in opponents:
            if self.negotiatingInfo.getPartnerBidNum(sender) % 10 == 0:
                ave = 0.
                extra = 0.

            m = self.negotiatingInfo.getAverage(sender)
            sd = self.negotiatingInfo.getStandardDeviation(sender)
            ave = m
            extra = sd

        c = 1 - math.pow(time, 5.)
        emax = self.emax()
        threshold = 1 - (1 - emax) * math.pow(time, 5.)

        return threshold

    def emax(self):
        ave = 0.
        extra = 0.
        sd = 0.

        for sender in self.negotiatingInfo.opponents:
            if self.negotiatingInfo.getPartnerBidNum(sender) % 10 == 0:
                ave = 0.
                extra = 0.

            m = self.negotiatingInfo.getAverage(sender)
            sd = self.negotiatingInfo.getStandardDeviation(sender)
            ave = m
            extra = sd

        d = math.sqrt(3) * sd / (math.sqrt(ave * (1 - ave)) + 1e-10)

        return 0.7 * ave + (1 - ave) * d * 0.7
