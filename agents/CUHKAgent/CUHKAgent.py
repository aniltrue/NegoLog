import math
import random
import time
from typing import List, Optional

import nenv
from agents.CUHKAgent.OwnBidHistory import OwnBidHistory
from agents.CUHKAgent.OpponentBidHistory import OpponentBidHistory


class CUHKAgent(nenv.AbstractAgent):
    """
        ANAC 2012 Winner [Hao2014]_

        .. [Hao2014] Hao, J., Leung, Hf. (2014). CUHKAgent: An Adaptive Negotiation Strategy for Bilateral Negotiations over Multiple Items. In: Marsa-Maestre, I., Lopez-Carmona, M., Ito, T., Zhang, M., Bai, Q., Fujita, K. (eds) Novel Insights in Agent-based Complex Automated Negotiation. Studies in Computational Intelligence, vol 535. Springer, Tokyo. <https://doi.org/10.1007/978-4-431-54758-7_11>
    """
    totalTime: float
    ActionOfOpponent: Optional[nenv.Action]
    maximumOfBid: float
    ownBidHistory: OwnBidHistory
    opponentBidHistory: OpponentBidHistory
    minimumUtilityThreshold: float
    utilityThreshold: float
    MaximumUtility: float
    timeLeftBefore: float
    timeLeftAfter: float
    maximumTimeOfOpponent: float
    maximumTimeOwn: float
    discountingFactor: float
    concedeToDiscountingFactor: float
    concedeToDiscountingFactor_original: float
    minConcedeToDiscountingFactor: float
    bidsBetweenUtility: List[List[nenv.Bid]]
    concedeToOpponent: bool
    toughAgent: bool

    alpha1: float
    bid_maximum_utility: nenv.Bid
    reservationValue: float
    rnd: random.Random

    def initiate(self, opponent_name: Optional[str]):
        self.ActionOfOpponent = None
        self.rnd = random.Random()
        self.maximumOfBid = len(self.preference.bids)
        self.ownBidHistory = OwnBidHistory()
        self.opponentBidHistory = OpponentBidHistory()
        self.bidsBetweenUtility = []
        self.bid_maximum_utility = self.preference.bids[0]
        self.utilityThreshold = self.bid_maximum_utility.utility
        self.MaximumUtility = self.utilityThreshold
        self.timeLeftAfter = 0
        self.timeLeftBefore = 0
        self.totalTime = self.session_time
        self.maximumTimeOfOpponent = 0
        self.maximumTimeOwn = 0
        self.minConcedeToDiscountingFactor = 0.08
        self.discountingFactor = 1

        self.chooseUtilityThreshold()
        self.calculateBidsBetweenUtility()
        self.chooseConcedeToDiscountingDegree()
        self.opponentBidHistory.initializeDataStructures(self.preference)
        self.timeLeftAfter = 0.
        self.concedeToOpponent = False
        self.toughAgent = False
        self.alpha1 = 2
        self.reservationValue = self.preference.reservation_value

    def receive_offer(self, bid: nenv.Bid, t: float):
        self.ActionOfOpponent = nenv.Offer(bid.copy())

    @property
    def name(self) -> str:
        return "CUHKAgent"

    def act(self, t: float) -> nenv.Action:
        start_time = time.time()
        action: nenv.Action

        self.timeLeftBefore = t
        bid: nenv.Bid

        if self.ActionOfOpponent is None or self.ActionOfOpponent.bid is None:
            bid = self.bid_maximum_utility
            action = nenv.Offer(bid)
        else:
            self.opponentBidHistory.updateOpponentModel(self.ActionOfOpponent.bid, self.preference)
            self.updateConcedeDegree()

            if len(self.ownBidHistory.BidHistory) == 0:
                bid = self.bid_maximum_utility
                action = nenv.Offer(bid)
            else:
                if self.estimateRoundLeft(True, t) > 10:
                    bid = self.BidToOffer(t)
                    IsAccept = self.AcceptOpponentOffer(self.ActionOfOpponent.bid, bid, t)

                    if IsAccept and self.can_accept():
                        action = self.accept_action
                    elif self.concedeToOpponent:
                        bid = self.opponentBidHistory.bid_maximum_from_opponent
                        action = nenv.Offer(bid)
                        self.toughAgent = True
                        self.concedeToOpponent = False
                    else:
                        action = nenv.Offer(bid)
                        self.toughAgent = False
                else:
                    if t > 0.9985 and self.estimateRoundLeft(True, t) < 5:
                        bid = self.opponentBidHistory.bid_maximum_from_opponent

                        if self.preference.get_utility(bid) < 0.85:
                            candidateBids = self.getBidsBetweenUtility(self.MaximumUtility - 0.15, self.MaximumUtility - 0.02)

                            if self.estimateRoundLeft(True, t) < 2:
                                bid = self.opponentBidHistory.bid_maximum_from_opponent
                            else:
                                bid = self.opponentBidHistory.ChooseBid(candidateBids, self.preference)

                            if bid is None:
                                bid = self.opponentBidHistory.bid_maximum_from_opponent

                        IsAccept = self.AcceptOpponentOffer(self.ActionOfOpponent.bid, bid, t)

                        if IsAccept and self.can_accept():
                            action = self.accept_action
                        elif self.toughAgent and self.can_accept():
                            action = self.accept_action
                        else:
                            action = nenv.Offer(bid)
                    else:
                        bid = self.BidToOffer(t)

                        IsAccept = self.AcceptOpponentOffer(self.ActionOfOpponent.bid, bid, t)

                        if IsAccept and self.can_accept():
                            action = self.accept_action
                        else:
                            action = nenv.Offer(bid)

        self.ownBidHistory.addBid(bid, self.preference)
        end_time = time.time()
        self.timeLeftAfter = t + (end_time - start_time) / self.totalTime if self.totalTime > 0 else t
        self.estimateRoundLeft(False, t)

        return action

    def BidToOffer(self, t: float):
        bidReturned: Optional[nenv.Bid] = None
        decreasingAmount_1 = 0.05
        decreasingAmount_2 = 0.25

        maximumOfBid = self.MaximumUtility
        minimumOfBid = 0.

        if self.discountingFactor == 1 and self.maximumOfBid > 3000:
            minimumOfBid = self.MaximumUtility - decreasingAmount_1

            if self.discountingFactor > 1 - decreasingAmount_2 and self.maximumOfBid > 10000 and t >= 0.98:
                minimumOfBid = self.MaximumUtility - decreasingAmount_2
            if self.utilityThreshold > minimumOfBid:
                self.utilityThreshold = minimumOfBid
        else:
            if t <= self.concedeToDiscountingFactor:
                minThershold = (maximumOfBid * self.discountingFactor) / math.pow(self.discountingFactor, self.concedeToDiscountingFactor)

                self.utilityThreshold = maximumOfBid - (maximumOfBid - minThershold) * math.pow(t / self.concedeToDiscountingFactor, self.alpha1)
            else:
                self.utilityThreshold = (maximumOfBid * self.discountingFactor) / math.pow(self.discountingFactor, t)
            minimumOfBid = self.utilityThreshold

        bestBidOfferedByOpponent = self.opponentBidHistory.bid_maximum_from_opponent

        if self.preference.get_utility(bestBidOfferedByOpponent) >= self.utilityThreshold or self.preference.get_utility(bestBidOfferedByOpponent) >= minimumOfBid:
            return bestBidOfferedByOpponent

        candidateBids = self.getBidsBetweenUtility(minimumOfBid, maximumOfBid)

        bidReturned = self.opponentBidHistory.ChooseBid(candidateBids, self.preference)

        if bidReturned is None:
            bidReturned = self.preference.bids[0].copy()

        return bidReturned

    def AcceptOpponentOffer(self, opponentBid: nenv.Bid, ownBid: nenv.Bid, t: float):
        currentUtility = self.preference.get_utility(opponentBid)
        maximumUtility = self.MaximumUtility
        nextRoundUtility = self.preference.get_utility(ownBid)

        if currentUtility >= self.utilityThreshold or currentUtility >= nextRoundUtility:
            return True

        predictMaximumUtility = maximumUtility * self.discountingFactor
        currentMaximumUtility = self.preference.get_utility(self.opponentBidHistory.bid_maximum_from_opponent)

        if currentMaximumUtility > predictMaximumUtility and t > self.concedeToDiscountingFactor:
            if self.preference.get_utility(opponentBid) >= self.preference.get_utility(self.opponentBidHistory.bid_maximum_from_opponent) - 0.01:
                return True
            else:
                self.concedeToOpponent = True
                return False
        elif currentMaximumUtility > self.utilityThreshold * math.pow(self.discountingFactor, t):
            if self.preference.get_utility(opponentBid) >= self.preference.get_utility(
                    self.opponentBidHistory.bid_maximum_from_opponent) - 0.01:
                return True
            else:
                self.concedeToOpponent = True
                return False
        else:
            return False

    def estimateRoundLeft(self, opponent: bool, t: float):
        if opponent:
            if self.timeLeftBefore - self.timeLeftAfter > self.maximumTimeOfOpponent:
                self.maximumTimeOfOpponent = self.timeLeftBefore - self.timeLeftAfter
        else:
            if self.timeLeftAfter - self.timeLeftBefore > self.maximumTimeOwn:
                self.maximumTimeOwn = self.timeLeftAfter - self.timeLeftBefore

        total_round = self.maximumTimeOfOpponent + self.maximumTimeOwn

        if total_round == 0:
            return float('inf')

        round = (self.totalTime - t * self.totalTime) // (total_round)

        return round

    def calculateBidsBetweenUtility(self):
        maximumUtility = self.MaximumUtility
        minUtility = self.minimumUtilityThreshold
        maximumRounds = int((maximumUtility - minUtility) // 0.01)

        for i in range(maximumRounds):
            self.bidsBetweenUtility.append([])

        self.bidsBetweenUtility[maximumRounds - 1].append(self.bid_maximum_utility)

        limits = 0

        if self.maximumOfBid < 20000:
            for bid in self.preference.bids:
                for i in range(maximumRounds):
                    if (i + 1) * 0.01 + minUtility >= self.preference.get_utility(bid) >= i * 0.01 + minUtility:
                        self.bidsBetweenUtility[i].append(bid.copy())
                        break
        else:
            while limits <= 20000:
                bid = self.preference.get_random_bid()

                for i in range(maximumRounds):
                    if (i + 1) * 0.01 + minUtility >= self.preference.get_utility(bid) >= i * 0.01 + minUtility:
                        self.bidsBetweenUtility[i].append(bid.copy())
                        break

                limits += 1

    def getBidsBetweenUtility(self, lowerBound, upperBound):
        bidsInRange = []

        rng = int((upperBound - self.minimumUtilityThreshold) // 0.01)
        initial = int((lowerBound - self.minimumUtilityThreshold) // 0.01)

        for i in range(initial, rng):
            bidsInRange.extend(self.bidsBetweenUtility[i])

        if len(bidsInRange) == 0:
            bidsInRange.append(self.bid_maximum_utility)

        return bidsInRange

    def chooseUtilityThreshold(self):
        self.minimumUtilityThreshold = 0

    def chooseConcedeToDiscountingDegree(self):
        alpha = 0.
        beta = 1.5

        if self.discountingFactor > 0.75:
            beta = 1.8
        elif self.discountingFactor > 0.5:
            beta = 1.5
        else:
            beta = 1.2

        alpha = math.pow(self.discountingFactor, beta)

        self.concedeToDiscountingFactor = self.minConcedeToDiscountingFactor + (1 - self.minConcedeToDiscountingFactor) * alpha
        self.concedeToDiscountingFactor_original = self.concedeToDiscountingFactor

    def updateConcedeDegree(self):
        gama = 10.
        weight = 0.1
        opponentToughnessDegree = self.opponentBidHistory.getConcessionDegree()

        self.concedeToDiscountingFactor = self.concedeToDiscountingFactor_original + weight * (1 - self.concedeToDiscountingFactor_original) * math.pow(opponentToughnessDegree, gama)

        if self.concedeToDiscountingFactor >= 1:
            self.concedeToDiscountingFactor = 1
