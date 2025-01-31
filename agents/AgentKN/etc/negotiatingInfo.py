import math
from typing import Optional

import nenv


class CntBySender:
    selectWeight: int
    opponents: list
    simpleCnt: dict
    simpleSum: int
    weightedCnt: dict
    weightedSum: float
    DownLiner: int = 0

    def __init__(self, selectWeight: int):
        self.selectWeight = selectWeight
        self.opponents = []
        self.simpleCnt = {}
        self.simpleSum = 0

        self.weightedCnt = {}
        self.weightedSum = 0.

    def incrementCnt(self, sender, t: float):
        self.simpleSum += 1

        if sender not in self.simpleCnt.keys():
            self.simpleCnt[sender] = 1
            self.opponents.append(sender)
        else:
            self.simpleCnt[sender] += 1

        addCnt = self.calWeightedIncrement(t)
        self.weightedSum += addCnt

        if sender not in self.weightedCnt.keys():
            self.weightedCnt[sender] = addCnt
        else:
            self.weightedCnt[sender] += addCnt

    def calWeightedIncrement(self, t: float):
        ans = 0.

        if self.selectWeight == self.DownLiner:
            ans = 1 - t

        return ans

    def getSimgpleCnt(self, sender):
        return self.simpleCnt.get(sender, 0)

    def getSimpleSum(self):
        return self.simpleSum


class negotiatingInfo:
    pref: nenv.Preference
    issues: list
    opponents: list
    my_bid_history: Optional[list] = None
    offeredValueNum: dict

    opponents_bid_history: Optional[dict] = None
    opponents_average: dict
    opponents_variance: dict
    opponents_sum: dict
    opponents_pow_sum: dict
    opponents_stdev: dict
    value_relative_utility: Optional[dict] = None

    all_value_frequency: Optional[dict] = None
    opponents_value_frequency: Optional[dict] = None
    round: int
    negotiator_num: int
    isLinerUtilitySpace: bool

    def __init__(self, preference: nenv.Preference):
        self.pref = preference
        self.issues = self.pref.issues.copy()
        self.round = 0
        self.negotiator_num = 0
        self.isLinerUtilitySpace = True
        self.opponents = []
        self.my_bid_history = []
        self.opponents_bid_history = {}
        self.opponents_average = {}
        self.opponents_variance = {}
        self.opponents_sum = {}
        self.opponents_pow_sum = {}
        self.opponents_stdev = {}
        self.value_relative_utility = {}
        self.offeredValueNum = {}

        self.initValueRelativeUtility()

    def initOpponent(self, sender):
        self.initNegotiatingInfo(sender)

        self.opponents.append(sender)

    def updateInfo(self, sender, offeredBid: nenv.Bid):
        self.updateNegotiatingInfo(sender, offeredBid)

    def initNegotiatingInfo(self, sender):
        self.opponents_bid_history[sender] = []
        self.opponents_average[sender] = 0.
        self.opponents_variance[sender] = 0.
        self.opponents_sum[sender] = 0.
        self.opponents_pow_sum[sender] = 0.
        self.opponents_stdev[sender] = 0.

    def initValueRelativeUtility(self):
        for issue in self.issues:
            self.value_relative_utility[issue] = {}

            values = issue.values

            for value in values:
                self.value_relative_utility[issue][value] = 0.

    def setValueRelativeUtility(self, maxBid: nenv.Bid):
        currentBid: Optional[nenv.Bid] = None

        for issue in self.issues:
            currentBid = maxBid.copy()
            for value in issue.values:
                currentBid[issue] = value

                self.value_relative_utility[issue][value] = self.pref.get_utility(currentBid) - self.pref.get_utility(maxBid)

    def updateNegotiatingInfo(self, sender, offeredBid: nenv.Bid):
        self.opponents_bid_history[sender].append(offeredBid)

        util = self.pref.get_utility(offeredBid)

        self.opponents_sum[sender] += util
        self.opponents_pow_sum[sender] += math.pow(util, 2)

        round_num = len(self.opponents_bid_history[sender])
        self.opponents_average[sender] = self.opponents_sum[sender] / round_num
        self.opponents_variance[sender] = (self.opponents_pow_sum[sender] / round_num) - math.pow(self.opponents_average[sender], 2)
        if self.opponents_variance[sender] < 0:
            self.opponents_variance[sender] = 0.

        self.opponents_stdev[sender] = math.sqrt(self.opponents_variance[sender])

    def updateOpponentsNum(self, num: int):
        self.negotiator_num = num

    def updateMyBidHistory(self, offeredBid: nenv.Bid):
        self.my_bid_history.append(offeredBid)

    def getAverage(self, sender):
        return self.opponents_average[sender]

    def getStandardDeviation(self, sender):
        return self.opponents_stdev[sender]

    def updateTimeScale(self, time: float):
        self.round += 1
        self.time_scale = time / self.round

    def getPartnerBidNum(self, sender):
        return len(self.opponents_bid_history[sender])

    def utilitySpaceTypeisNonLiner(self):
        self.isLinerUtilitySpace = False

    def getHighFrequencyValue(self, sender, issue: nenv.Issue):
        values = issue.values
        tempMax = 0.
        tempValue = values[0]

        for value in values:
            if value in self.offeredValueNum.keys():
                nowCnt = self.offeredValueNum[value].getSimpleCnt(sender)

                if tempMax < nowCnt:
                    tempMax = nowCnt
                    tempValue = value

        return tempValue

    def updateOfferedValueNum(self, sender, bid: nenv.Bid, t: float):
        for issue in self.issues:
            value = bid[issue]

            if value not in self.offeredValueNum.keys():
                self.offeredValueNum[value] = CntBySender(0)

            self.offeredValueNum[value].incrementCnt(sender, t)

    def getBidFrequency(self, bid: nenv.Bid):
        tPoint = 0

        for issue, value in bid:
            if value in self.offeredValueNum.keys():
                tPoint += self.offeredValueNum[value].getSimpleSum()

        return tPoint
