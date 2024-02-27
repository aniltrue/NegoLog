import math
from typing import List, Dict

import nenv


class NegotiatingInfo:
    pref: nenv.Preference
    issues: List[nenv.Issue]
    opponents: List[str]
    MyBidHistory: List[nenv.Bid]
    opponentsBidHistory: Dict[str, List[nenv.Bid]]
    opponentsBool: Dict[str, bool]
    opponentsAverage: Dict[str, float]
    opponentsVariance: Dict[str, float]
    opponentsSum: Dict[str, float]
    opponentsPowSum: Dict[str, float]
    opponentsStd: Dict[str, float]
    valueRelativeUtility: Dict[nenv.Issue, Dict[str, float]]

    round: int
    negotiatorNum: int
    isLinerUtilitySpace: bool

    def __init__(self, pref: nenv.Preference):
        self.pref = pref
        self.round = 0
        self.negotiatorNum = 2
        self.isLinerUtilitySpace = True
        self.opponents = []
        self.MyBidHistory = []
        self.opponentsBidHistory = {}
        self.opponentsBool = {}
        self.opponentsAverage = {}
        self.opponentsVariance = {}
        self.opponentsSum = {}
        self.opponentsPowSum = {}
        self.opponentsStd = {}
        self.valueRelativeUtility = {}
        self.issues = pref.issues

        self.initValueRelativeUtility()

    def initOpponent(self, sender: str):
        self.initNegotiatingInfo(sender)
        self.opponents.append(sender)

    def updateInfo(self, sender: str, offeredBid: nenv.Bid):
        self.updateNegotiatingInfo(sender, offeredBid)

    def initNegotiatingInfo(self, sender):
        self.opponentsBidHistory[sender] = []
        self.opponentsAverage[sender] = 0.
        self.opponentsVariance[sender] = 0.
        self.opponentsSum[sender] = 0.
        self.opponentsPowSum[sender] = 0.
        self.opponentsStd[sender] = 0.

    def initValueRelativeUtility(self):
        for issue in self.issues:
            self.valueRelativeUtility[issue] = {value: 0. for value in issue.values}

    def setValueRelativeUtility(self, maxBid: nenv.Bid):
        for issue in self.issues:
            currentBid = maxBid.copy()
            values = issue.values

            for value in values:
                currentBid[issue] = value
                self.valueRelativeUtility[issue][value] = self.pref.get_utility(currentBid) - self.pref.get_utility(maxBid)

    def updateNegotiatingInfo(self, sender: str, offeredBid: nenv.Bid):
        self.opponentsBidHistory[sender].append(offeredBid.copy())

        util = self.pref.get_utility(offeredBid)

        self.opponentsSum[sender] += util
        self.opponentsPowSum[sender] += util * util

        round_num = len(self.opponentsBidHistory[sender])
        self.opponentsAverage[sender] = self.opponentsSum[sender] / round_num
        self.opponentsVariance[sender] = (self.opponentsPowSum[sender] / round_num) - math.pow(self.opponentsAverage[sender], 2)

        if self.opponentsVariance[sender] < 0:
            self.opponentsVariance[sender] = 0.

        self.opponentsStd[sender] = math.sqrt(self.opponentsVariance[sender])

    def getOpponentsBool(self, sender: str):
        if len(self.opponentsBool):
            return False

        return self.opponentsBool.get(sender, False)

