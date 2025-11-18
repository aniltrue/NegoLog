import math
import random
from typing import List, Dict, Optional
import nenv


class OpponentBidHistory:
    bidHistory: List[nenv.Bid]
    opponentBidsStatisticsForDiscrete: List[Dict[str, int]]
    maximumBidsStored: int
    bidCounter: Dict[nenv.Bid, int]
    bid_maximum_from_opponent: Optional[nenv.Bid]

    def __init__(self):
        self.bidHistory = []
        self.maximumBidsStored = 100
        self.bid_maximum_from_opponent = None
        self.bidCounter = {}
        self.opponentBidsStatisticsForDiscrete = []

    def addBid(self, bid: nenv.Bid, pref: nenv.Preference):
        if bid not in self.bidHistory:
            self.bidHistory.append(bid)

        if len(self.bidHistory) == 1:
            self.bid_maximum_from_opponent = self.bidHistory[0].copy()
        else:
            if pref.get_utility(bid) > pref.get_utility(self.bid_maximum_from_opponent):
                self.bid_maximum_from_opponent = bid.copy()

    def initializeDataStructures(self, pref: nenv.Preference):
        issues = pref.issues

        for lIssue in issues:
            self.opponentBidsStatisticsForDiscrete.append({value: 0 for value in lIssue.values})

    def updateOpponentModel(self, bidToUpdate: nenv.Bid, pref: nenv.Preference):
        self.addBid(bidToUpdate, pref)

        self.bidCounter[bidToUpdate] = self.bidCounter.get(bidToUpdate, 0) + 1

        if len(self.bidHistory) <= self.maximumBidsStored:
            self.updateStatistics(bidToUpdate, False, pref)

    def updateStatistics(self, bidToUpdate: nenv.Bid, toRemove: bool, pref: nenv.Preference):
        issues = pref.issues

        discreteIndex = 0

        for issueNum, issue in enumerate(issues):
            v = bidToUpdate[issue]

            if self.opponentBidsStatisticsForDiscrete is None:
                pass
            elif self.opponentBidsStatisticsForDiscrete[discreteIndex][v] is not None:
                counterPerValue = self.opponentBidsStatisticsForDiscrete[discreteIndex][v]

                if toRemove:
                    counterPerValue -= 1
                else:
                    counterPerValue += 1

                self.opponentBidsStatisticsForDiscrete[discreteIndex][v] = counterPerValue

            discreteIndex += 1

    def ChooseBid(self, candidateBids: list, pref: nenv.Preference):
        upperSearchLimit = 200

        maxIndex = -1
        ran = random.Random()
        issues = pref.issues

        maxFrequency = 0
        discreteIndex = 0

        if len(candidateBids) >= upperSearchLimit:
            candidateBids = ran.sample(candidateBids, upperSearchLimit)

        for i in range(len(candidateBids)):
            maxValue = 0
            discreteIndex = 0

            for j in range(len(issues)):
                v = candidateBids[i][issues[j]]

                if self.opponentBidsStatisticsForDiscrete is None:
                    pass
                elif self.opponentBidsStatisticsForDiscrete[discreteIndex] is not None:
                    counterPerValue = self.opponentBidsStatisticsForDiscrete[discreteIndex][v]
                    maxValue += counterPerValue

                discreteIndex += 1

            if maxValue > maxFrequency:
                maxFrequency = maxValue
                maxIndex = i
            elif maxValue == maxFrequency:
                if ran.random() < 0.5:
                    maxFrequency = maxValue
                    maxIndex = i

        if maxIndex == -1:
            return ran.choice(candidateBids)
        else:
            if ran.random() < 0.95:
                return candidateBids[maxIndex]
            else:
                return ran.choice(candidateBids)

    def chooseBestFromHistory(self, pref: nenv.Preference):
        max = -1
        maxBid = None

        for bid in self.bidHistory:
            if max < pref.get_utility(bid):
                maxBid = bid
                max = pref.get_utility(bid)

        return maxBid

    def concedeDegree(self, pref: nenv.Preference):
        numOfBids = len(self.bidHistory)
        bidCounter = {}

        for i in range(numOfBids):
            bidCounter[self.bidHistory[i]] = bidCounter.get(self.bidHistory[i], 0) + 1

        return len(bidCounter) / len(pref.bids)

    def StandardDeviationMean(self, data: list):
        mean = 0
        n = len(data)

        if n < 2:
            return None

        for i in range(n):
            mean += data[i]

        mean /= n

        sum = 0

        for i in range(n):
            v = data[i] - mean
            sum += v * v

        return math.sqrt(sum / (n - 1))

    def getSize(self):
        numOfBids = len(self.bidHistory)

        bidCounter = {}

        for i in range(numOfBids):
            bidCounter[self.bidHistory[i]] = bidCounter.get(self.bidHistory[i], 0) + 1

        return len(bidCounter)

    def getConcessionDegree(self):
        numOfBids = len(self.bidHistory)
        numOfDistinctBid = 0
        historyLength = 10
        concessionDegree = 0.

        if numOfBids - historyLength > 0:
            for j in range(numOfBids - historyLength, numOfBids):
                if self.bidCounter[self.bidHistory[j]] == 1:
                    numOfDistinctBid += 1

            concessionDegree = math.pow(numOfDistinctBid / historyLength, 2)
        else:
            numOfDistinctBid = self.getSize()
            concessionDegree = math.pow(numOfDistinctBid / historyLength, 2)

        return concessionDegree
