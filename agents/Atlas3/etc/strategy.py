import math
from typing import Optional

import nenv
from agents.Atlas3.etc.negotiatingInfo import negotiatingInfo


class strategy:
    pref: nenv.Preference
    negotiatingInfo: negotiatingInfo

    df: float
    rv: float

    A11: float
    A12: float
    A21: float
    A22: float

    TF: float = 1.0
    PF: float = 0.5

    def __init__(self, pref: nenv.Preference, negotiatingInfo):
        self.A11, self.A12, self.A21, self.A22 = 0., 0., 0., 0.

        self.pref = pref
        self.negotiatingInfo = negotiatingInfo

        self.rv = self.pref.reservation_value
        self.df = 1.

    def selectAccept(self, offeredBid: Optional[nenv.Bid], time: float):
        if offeredBid is None:
            return False

        offeredBidUtil = self.pref.get_utility(offeredBid)

        if offeredBidUtil >= self.getThreshold(time):
            return True

        return False

    def selectEndNegotiation(self, time: float):
        if self.rv * math.pow(self.df, time) >= self.getThreshold(time):
            return True

        return False

    def getThreshold(self, time: float) -> float:
        threshold = 1.0

        self.updateGameMatrix()

        target = self.getExpectedUtilityinFOP() / math.pow(self.df, time)

        if self.df == 1.0:
            threshold = target + (1.0 - target) * (1.0 - time)
        else:
            threshold = max(1.0 - time / self.df, target)

        return threshold

    def getExpectedUtilityinFOP(self):
        q = self.getOpponentEES()

        return q * self.A21 + (1- q) * self.A22

    def getOpponentEES(self):
        q = 1.0

        if self.A12 - self.A22 != 0 and 1. - (self.A11 - self.A21)/(self.A12 - self.A22) != 0:
            q = 1. / (1. - (self.A11 - self.A21)/(self.A12 - self.A22))

        if q < 0. or q > 1.:
            q = 1.

        return q

    def updateGameMatrix(self):
        C: float

        if self.negotiatingInfo.negotiator_num == 2:
            C = self.negotiatingInfo.BOU
        else:
            C = self.negotiatingInfo.MPBU

        self.A11 = self.rv * self.df
        self.A12 = math.pow(self.df, self.TF)

        if C >= self.rv:
            self.A21 = C * math.pow(self.df, self.TF)
        else:
            self.A21 = self.rv * self.df

        self.A22 = self.PF * self.A21 + (1. - self.PF) * self.A12
