import math
import random
from typing import Optional

import numpy as np
import nenv
from agents.Atlas3.etc.negotiatingInfo import negotiatingInfo


class bidSearch:
    maxBid: Optional[nenv.Bid] = None
    negotiatingInfo: negotiatingInfo
    NEAR_ITERATION = 1
    SA_ITERATION = 1
    START_TEMPERATURE = 1.0
    END_TEMPERATURE = 0.0001
    COOL = 0.999
    STEP = 1
    STEP_NUM = 1
    pref: nenv.Preference

    def __init__(self, preference: nenv.Preference, negotiatingInfo):
        self.pref = preference
        self.negotiatingInfo = negotiatingInfo
        self.initMaxBid()
        self.negotiatingInfo.setValueRelativeUtility(self.maxBid)

    def initMaxBid(self):
        tryNum = len(self.pref.issues)
        self.maxBid = self.pref.get_random_bid()

        for i in range(tryNum):
            self.SimulatedAnnealingSearch(self.maxBid, 1.0)

            while self.pref.get_utility(self.maxBid) < self.pref.reservation_value:
                self.SimulatedAnnealingSearch(self.maxBid, 1.0)

            if self.pref.get_utility(self.maxBid) == 1.0:
                break

    def getBid(self, baseBid: nenv.Bid, threshold: float):
        bid = self.getBidbyNeighborhoodSearch(baseBid, threshold)

        if self.pref.get_utility(bid) < threshold:
            bid = self.getBidbyAppropriateSearch(baseBid, threshold)
        if self.pref.get_utility(bid) < threshold:
            bid = self.maxBid.copy()

        bid = self.getConvertBidbyFrequencyList(bid)

        return bid

    def getBidbyNeighborhoodSearch(self, baseBid: nenv.Bid, threshold: float) -> nenv.Bid:
        bid = baseBid.copy()

        for i in range(self.NEAR_ITERATION):
            bid = self.NeighborhoodSearch(bid, threshold)

        return bid

    def getBidbyAppropriateSearch(self, baseBid: nenv.Bid, threshold: float) -> nenv.Bid:
        bid = baseBid.copy()

        if self.negotiatingInfo.isLinerUtilitySpace:
            bid = self.relativeUtilitySearch(threshold)

            if self.pref.get_utility(bid) < threshold:
                self.negotiatingInfo.utilitySpaceTypeisNonLiner()

        if not self.negotiatingInfo.isLinerUtilitySpace:
            current_bid = None
            current_bid_util = 0.
            min = 1.0

            for i in range(self.SA_ITERATION):
                current_bid = self.SimulatedAnnealingSearch(bid, threshold)
                current_bid_util = self.pref.get_utility(current_bid)

                if current_bid_util <= min and current_bid_util >= threshold:
                    bid = current_bid.copy()
                    min = current_bid_util

        return bid

    def relativeUtilitySearch(self, threshold: float) -> nenv.Bid:
        bid = self.maxBid.copy()
        d = threshold - 1.0
        concessionSum = 0.
        relativeUtility = 0.

        value_relative_utility = self.negotiatingInfo.value_relative_utility
        issues = self.negotiatingInfo.issues.copy()
        np.random.shuffle(issues)

        for issue in issues:
            randomValues = issue.values.copy()
            np.random.shuffle(randomValues)

            for value in randomValues:
                relativeUtility = value_relative_utility[issue][value]

                if d <= concessionSum + relativeUtility:
                    bid[issue] = value
                    concessionSum += relativeUtility
                    break

        return bid

    def SimulatedAnnealingSearch(self, baseBid: nenv.Bid, threhold: float) -> nenv.Bid:
        current_bid = baseBid.copy()
        current_bid_util = self.pref.get_utility(baseBid)
        next_bid = None
        next_bid_utility = 0.
        targetBids = []
        target_bid_util = 0.
        p: float
        randomnr = random.Random()

        currentTempreature = self.START_TEMPERATURE
        newCost = 1.0
        current_cost = 1.0
        issues = self.pref.issues.copy()

        while currentTempreature > self.END_TEMPERATURE:
            next_bid = current_bid.copy()
            for i in range(self.STEP_NUM):
                issue = randomnr.choice(issues)
                value = randomnr.choice(issue.values)

                next_bid[issue] = value
                next_bid_utility = self.pref.get_utility(next_bid)

                if self.maxBid == None or next_bid_utility >= self.pref.get_utility(self.maxBid):
                    self.maxBid = next_bid.copy()

            newCost = abs(threhold - next_bid_utility)
            current_cost = abs(threhold - current_bid_util)

            p = math.exp(-(abs(newCost - current_cost)) / currentTempreature)

            if newCost < current_cost or p > randomnr.random():
                current_bid = next_bid.copy()
                current_bid_util = next_bid_utility

            if current_bid_util >= threhold:
                if len(targetBids) == 0:
                    targetBids.append(current_bid.copy())
                    target_bid_util = self.pref.get_utility(current_bid)
                else:
                    if current_bid_util < target_bid_util:
                        targetBids = [current_bid.copy()]
                        target_bid_util = self.pref.get_utility(current_bid)
                    elif current_bid_util == target_bid_util:
                        targetBids.append(current_bid.copy())

            currentTempreature = currentTempreature * self.COOL

        if len(targetBids) == 0:
            return baseBid.copy()
        else:
            return randomnr.choice(targetBids).copy()

    def NeighborhoodSearch(self, baseBid: nenv.Bid, threshold: float) -> nenv.Bid:
        current_bid = baseBid.copy()
        current_bid_util = self.pref.get_utility(baseBid)

        target_bids = []
        target_bid_util = 0.
        randomnr = random.Random()
        values = []
        issues = self.pref.issues.copy()

        for issue in issues:
            values = issue.values.copy()
            for value in values:
                current_bid[issue] = value
                current_bid_util = self.pref.get_utility(current_bid)

                if self.maxBid is None or current_bid_util >= self.pref.get_utility(self.maxBid):
                    self.maxBid = current_bid.copy()

                if current_bid_util >= threshold:
                    if len(target_bids) == 0:
                        target_bids.append(current_bid.copy())
                        target_bid_util = self.pref.get_utility(current_bid)
                    else:
                        if current_bid_util < target_bid_util:
                            target_bids = [current_bid.copy()]
                            target_bid_util = self.pref.get_utility(current_bid)
                        elif current_bid_util == target_bid_util:
                            target_bids.append(current_bid.copy())

            current_bid = baseBid.copy()

        if len(target_bids) == 0:
            return baseBid.copy()
        else:
            return randomnr.choice(target_bids).copy()

    def getConvertBidbyFrequencyList(self, baseBid: nenv.Bid) -> nenv.Bid:
        current_bid = baseBid.copy()

        randomOrderOpponents = self.negotiatingInfo.opponents.copy()
        np.random.shuffle(randomOrderOpponents)

        randomOrderIssues = self.pref.issues.copy()
        np.random.shuffle(randomOrderIssues)

        for issue in randomOrderIssues:
            next_bid = current_bid.copy()
            next_bid[issue] = self.negotiatingInfo.getValueByAllFrequencyList(issue)

            if self.pref.get_utility(next_bid) >= self.pref.get_utility(current_bid):
                current_bid = next_bid.copy()

        return current_bid

    def criticalIssue(self, baseBid: nenv.Bid) -> list:
        current_bid = baseBid.copy()
        critical_issues = []
        values = []
        issues = self.pref.issues.copy()

        for issue in issues:
            values = issue.values.copy()

            for value in values:
                current_bid[issue] = value

                if self.pref.get_utility(current_bid) != self.pref.get_utility(baseBid):
                    critical_issues.append(issue)
                    break

            current_bid = baseBid.copy()

        return critical_issues
