import math
import random
from typing import Optional
import nenv
from agents.Kawaii.NegotiatingInfo import NegotiatingInfo


class BidSearch:
    pref: nenv.Preference
    negotiatingInfo: NegotiatingInfo
    maxBid: Optional[nenv.Bid]

    SA_ITERATION: int = 1
    START_TEMPERATURE: float = 1.
    END_TEMPERATURE: float = 0.0001
    COOL: float = 0.999

    STEP: int = 1
    STEP_NUM: int = 1

    def __init__(self, pref: nenv.Preference, negotiatingInfo: NegotiatingInfo):
        self.pref = pref
        self.negotiatingInfo = negotiatingInfo
        self.maxBid = None

        self.initMaxBid()

        self.negotiatingInfo.setValueRelativeUtility(self.maxBid)

    def initMaxBid(self):
        tryNum = len(self.pref.issues)

        self.maxBid = self.pref.get_random_bid()

        for i in range(tryNum):
            self.SimulatedAnnealingSearch(self.maxBid, 1.)

            while self.pref.reservation_value >= self.pref.get_utility(self.maxBid):
                self.SimulatedAnnealingSearch(self.maxBid, 1.)

            if self.pref.get_utility(self.maxBid) == 1.:
                break

    def getBid(self, baseBid: nenv.Bid, threshold: float):
        bid = self.getBidbyAppropriateSearch(baseBid, threshold)

        if self.pref.get_utility(bid) < threshold:
            return self.maxBid.copy()

        return bid

    def getBidbyAppropriateSearch(self, baseBid: nenv.Bid, threshold: float):
        bid = baseBid.copy()

        if self.negotiatingInfo.isLinerUtilitySpace:
            bid = self.relativeUtilitySearch(threshold)

            if self.pref.get_utility(bid) < threshold:
                self.negotiatingInfo.isLinerUtilitySpace = False

        if not self.negotiatingInfo.isLinerUtilitySpace:
            currentBid: nenv.Bid
            currentBidUtil = 0.
            min = 1.

            for i in range(self.SA_ITERATION):
                currentBid = self.SimulatedAnnealingSearch(bid, threshold)
                currentBidUtil = self.pref.get_utility(currentBid)

                if currentBidUtil <= min and currentBidUtil >= threshold:
                    bid = currentBid.copy()
                    min = currentBidUtil

        return bid

    def relativeUtilitySearch(self, threshold: float):
        bid = self.maxBid.copy()
        d = threshold - 1.
        concessionSum = 0.
        relativeUtility = 0.

        valueRelativeUtility = self.negotiatingInfo.valueRelativeUtility

        randomIssues = self.pref.issues
        random.shuffle(randomIssues)
        randomValues: list

        for issue in randomIssues:
            randomValues = issue.values
            random.shuffle(randomValues)

            for value in randomValues:
                relativeUtility = valueRelativeUtility[issue][value]

                if d <= concessionSum + relativeUtility:
                    bid[issue] = value
                    concessionSum += relativeUtility
                    break

        return bid

    def SimulatedAnnealingSearch(self, baseBid: nenv.Bid, threshold: float):
        currentBid = baseBid.copy()
        currentBidUtil = self.pref.get_utility(currentBid)

        nextBid: nenv.Bid
        nextBidUtil = 0.

        targetBids = []
        targetBidUtil = 0.
        p: float = 0.
        randomnr = random.Random()

        currentTemperature = self.START_TEMPERATURE
        newCost = 1.
        currentCost = 1.

        issues = self.pref.issues

        while currentTemperature > self.END_TEMPERATURE:
            nextBid = currentBid.copy()

            for i in range(self.STEP_NUM):
                issue = randomnr.choice(issues)
                value = randomnr.choice(issue.values)

                nextBid[issue] = value
                nextBidUtil = self.pref.get_utility(nextBid)

                if self.maxBid is None or nextBidUtil >= self.pref.get_utility(self.maxBid):
                    self.maxBid = nextBid.copy()

            newCost = abs(threshold - nextBidUtil)
            currentCost = abs(threshold - currentBidUtil)

            p = math.exp(-abs(newCost - currentCost) / currentTemperature)

            if newCost < currentCost or p > randomnr.random():
                currentBid = nextBid.copy()
                currentBidUtil = nextBidUtil

            if currentBidUtil >= threshold:
                if len(targetBids) == 0:
                    targetBids.append(currentBid.copy())
                    targetBidUtil = self.pref.get_utility(currentBid)
                else:
                    if currentBidUtil < targetBidUtil:
                        targetBids = [currentBid.copy()]
                        targetBidUtil = self.pref.get_utility(currentBid)
                    elif currentBidUtil == targetBidUtil:
                        targetBids.append(currentBid.copy())

            currentTemperature *= self.COOL

        if len(targetBids) == 0:
            return baseBid.copy()

        return randomnr.choice(targetBids).copy()
