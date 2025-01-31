import math
import random
from typing import Dict, Optional

import nenv
from agents.AgentBuyog.Regression import Regression
from agents.AgentBuyog.OpponentInfo import OpponentInfo
from agents.NiceTitForTat.helpers.BidHistory import BidHistory, BidDetails


class AgentBuyog(nenv.AbstractAgent):
    """
        AgentBuyog estimates the concession function of the opponent. [Fujita2017]_

        ANAC 2015 individual utility category runner-up.

        .. [Fujita2017] Fujita, K., Aydoğan, R., Baarslag, T., Hindriks, K., Ito, T., Jonker, C. (2017). The Sixth Automated Negotiating Agents Competition (ANAC 2015). In: Fujita, K., et al. Modern Approaches to Agent-based Complex Automated Negotiation. Studies in Computational Intelligence, vol 674. Springer, Cham. https://doi.org/10.1007/978-3-319-51563-2_9
    """
    alphaDefault: float
    betaDefault: float
    issueWeightsConstant: float
    issueValuesConstant: float
    minimumHistorySize: float
    learningTimeController: float
    maxWeightForBidPoint: int
    leniencyAdjuster: float
    domainWeightController: float
    timeConcessionController: float
    lastSecondConcessionFactor: float
    kalaiPointCorrection: float
    kalaiPointUpdate: Dict[str, int]
    infoA: Optional[OpponentInfo]
    infoB: Optional[OpponentInfo]
    myBidHistory: BidHistory
    AandBscommonBids: BidHistory
    totalHistory: BidHistory
    initialized: bool
    numberOfRounds: int

    def initiate(self, opponent_name: Optional[str]):
        self.alphaDefault = 0.
        self.betaDefault = 0.
        self.issueWeightsConstant = 0.3
        self.issueValuesConstant = 100
        self.minimumHistorySize = 50
        self.learningTimeController = 1.3
        self.maxWeightForBidPoint = 300
        self.leniencyAdjuster = 1.
        self.domainWeightController = 1.75
        self.timeConcessionController = 1.8
        self.lastSecondConcessionFactor = 0.5
        self.kalaiPointCorrection = 0.1
        self.kalaiPointUpdate = {}
        self.infoA = None
        self.infoB = None
        self.totalHistory = BidHistory()
        self.myBidHistory = BidHistory()
        self.AandBscommonBids = BidHistory()
        self.initialized = False
        self.numberOfRounds = 0

    @property
    def name(self) -> str:
        return "AgentBuyog"

    def act(self, t: float) -> nenv.Action:
        self.numberOfRounds += 1

        timePerRound = t / self.numberOfRounds
        remainingRounds = (1 - t) / (timePerRound + 1e-10)

        bestBid = None
        minimumPoint = 1. * 0.7 + self.preference.reservation_value * 0.3
        bestAgreeableBidSoFar = None
        bestAgreeableBidsUtility = 0.
        mostRecentBidsUtility = 0.

        if len(self.AandBscommonBids.history) > 0:
            bestAgreeableBidSoFar = self.AandBscommonBids.getBestBidDetails()
            bestAgreeableBidsUtility = bestAgreeableBidSoFar.utility

        if len(self.totalHistory.history) > 0:
            mostRecentBidsUtility = self.totalHistory.history[-1].utility

        difficultAgent: Optional[OpponentInfo] = None

        if self.infoA is not None and self.infoB is not None and self.infoA.agentDifficulty is not None and self.infoB.agentDifficulty is not None:
            if self.infoA.agentDifficulty <= self.infoB.agentDifficulty:
                difficultAgent = self.infoA
            else:
                difficultAgent = self.infoB

            minimumPoint = 1 * difficultAgent.agentDifficulty

        acceptanceThreshold = minimumPoint + (1 - minimumPoint) * (1 - math.pow(t, self.timeConcessionController))

        if remainingRounds <= 3:
            acceptanceThreshold = acceptanceThreshold * self.lastSecondConcessionFactor

        if acceptanceThreshold < self.preference.reservation_value:
            acceptanceThreshold = self.preference.reservation_value

        if self.can_accept() and mostRecentBidsUtility >= acceptanceThreshold and mostRecentBidsUtility >= bestAgreeableBidsUtility and remainingRounds <= 3:
            return self.accept_action

        if bestAgreeableBidsUtility > acceptanceThreshold:
            bestBid = bestAgreeableBidSoFar
        else:
            bidsInWindow = [BidDetails(bid, bid.utility, t) for bid in self.preference.get_bids_at(acceptanceThreshold, 0., 1.)]
            bestBid = self.getBestBidFromList(bidsInWindow)

        if self.can_accept() and mostRecentBidsUtility >= acceptanceThreshold and mostRecentBidsUtility >= bestAgreeableBidsUtility and mostRecentBidsUtility >= bestBid.utility:
            return self.accept_action

        self.totalHistory.add(bestBid)

        return nenv.Offer(bestBid.bid)

    def getBestBidFromList(self, bidsInWindow: list):
        if self.infoA is None or self.infoB is None or self.infoA.agentDifficulty is None or self.infoB.agentDifficulty is None:
            return random.choice(bidsInWindow)

        bestBid = self.findNearestBidToKalai(bidsInWindow, 1., 1.)

        return bestBid

    def findNearestBidToKalai(self, bidsInWindow: list, infoAKalai: float, infoBKalai: float):
        nearestBid: BidDetails = bidsInWindow[0]
        shortestDistance: float = self.getDistance(nearestBid, infoAKalai, infoBKalai)

        for bid in bidsInWindow:
            bidDistance = self.getDistance(bid, infoAKalai, infoBKalai)

            if bidDistance < shortestDistance:
                shortestDistance = bidDistance
                nearestBid = bid

        return nearestBid

    def getDistance(self, bid: BidDetails, infoAKalai: float, infoBKalai: float):
        return math.sqrt((1 - self.infoA.agentDifficulty) * math.pow(self.infoA.pref.get_utility(bid.bid), 2.) +
                         (1 - self.infoB.agentDifficulty) * math.pow(self.infoB.pref.get_utility(bid.bid), 2.))

    def receive_offer(self, bid: nenv.Bid, t: float):
        if not self.initialized:
            self.initializeOpponentInfo("OpponentAgent")

        self.totalHistory.add(BidDetails(bid, bid.utility, t))

        senderInfo = self.getOpponentInfoObjectOfSender("OpponentAgent")
        otherInfo = self.getOpponentInfoObjectOfOther("OpponentAgent")
        self.updateOpponentBidHistory(senderInfo, bid, t)
        self.updateCommonBids(otherInfo, bid)
        self.updateOpponentModel(senderInfo, t)

    def updateCommonBids(self, otherInfo: OpponentInfo, bid: nenv.Bid):
        if otherInfo is None:
            return

        if otherInfo.containsBid(bid):
            self.AandBscommonBids.add(BidDetails(bid, bid.utility))

    def getOpponentInfoObjectOfOther(self, sender):
        if self.infoA is not None and self.infoA.agentID == sender:
            return self.infoB
        elif self.infoB is not None and self.infoB.agentID == sender:
            return self.infoA

        return None

    def updateOpponentModel(self, senderInfo: OpponentInfo, t: float):
        if senderInfo.agentID not in self.kalaiPointUpdate:
            self.kalaiPointUpdate[senderInfo.agentID] = 0

        if len(senderInfo.agentBidHistory.history) >= self.minimumHistorySize:
            x_data = [bid.time for bid in senderInfo.agentBidHistory.history]
            y_data = [bid.utility for bid in senderInfo.agentBidHistory.history]
            y_weights_data = [w for w in senderInfo.bidPointWeights]

            regression = Regression(senderInfo.agentBidHistory.history[0].utility)
            regression.fit(x_data, y_data, y_weights_data)

            alpha = regression.w1
            beta = regression.w2

            slopeStandardScale = math.exp(alpha) * beta * math.pow(t, beta - 1)
            slopeFromZeroToOne = math.atan(slopeStandardScale) / (math.pi / 2.)
            adjustedLeniency = slopeFromZeroToOne + slopeFromZeroToOne / self.leniencyAdjuster

            if adjustedLeniency > 1:
                adjustedLeniency = 1.

            senderInfo.leniency = adjustedLeniency
        else:
            senderInfo.leniency = -1.

        opponentUtilitySpace = senderInfo.pref

        if len(senderInfo.agentBidHistory.history) < 2:
            return

        numberOfUnchanged = 0
        numberOfIssues = len(self.preference.issues)

        opponentsBidHistory = senderInfo.agentBidHistory
        opponentsLatestBid = opponentsBidHistory.history[-1]
        opponentsSecondLastBid = opponentsBidHistory.history[-2]

        changed = self.determineDifference(senderInfo, opponentsSecondLastBid, opponentsLatestBid)

        for hasChanged in changed.values():
            if not hasChanged:
                numberOfUnchanged += 1

        goldenValue = self.issueWeightsConstant * (1 - (math.pow(t, self.learningTimeController + 1.))) / numberOfIssues

        totalSum = 1. + goldenValue * numberOfUnchanged
        maximumWeight = 1. - numberOfIssues * goldenValue / totalSum

        for issue in changed.keys():
            if not changed[issue] and opponentUtilitySpace.issue_weights[issue] < maximumWeight:
                opponentUtilitySpace[issue] = (opponentUtilitySpace[issue] + goldenValue) / totalSum
            else:
                opponentUtilitySpace[issue] = opponentUtilitySpace[issue] / totalSum

        for issue in opponentUtilitySpace.issues:
            opponentUtilitySpace[issue, opponentsLatestBid.bid[issue]] = opponentUtilitySpace[issue, opponentsLatestBid.bid[issue]] + self.issueValuesConstant * math.pow(t, self.learningTimeController + 1.)

        opponentUtilitySpace.normalize()

        if self.kalaiPointUpdate[senderInfo.agentID] % 5 == 0:
            kalaiPoint = self.get_estimated_kalai_value(opponentUtilitySpace)

            self.kalaiPointUpdate[senderInfo.agentID] += 1

            if kalaiPoint <= 0.4:
                kalaiPoint += self.kalaiPointCorrection
            elif kalaiPoint <= 0.7:
                kalaiPoint += self.kalaiPointCorrection / 2.

            if kalaiPoint > senderInfo.bestBids.getBestBidDetails().utility:
                senderInfo.domainCompetitiveness = kalaiPoint
            else:
                senderInfo.domainCompetitiveness = senderInfo.bestBids.getBestBidDetails().utility

            if len(senderInfo.agentBidHistory.history) >= self.minimumHistorySize:
                try:
                    domainWeight = (1 - math.pow(senderInfo.leniency, self.domainWeightController))

                    agentDifficulty = (1 - domainWeight) * senderInfo.leniency + domainWeight * senderInfo.domainCompetitiveness

                    senderInfo.agentDifficulty = agentDifficulty
                except:
                    senderInfo.agentDifficulty = senderInfo.domainCompetitiveness
            else:
                agentDifficulty = senderInfo.domainCompetitiveness

                senderInfo.agentDifficulty = agentDifficulty

    def get_estimated_kalai_value(self, estimated_preference: nenv.OpponentModel.EstimatedPreference) -> float:
        """
            This method finds the utility of the agent where the Social Welfare is maximum.
        :param estimated_preference: Estimated opponent preferences
        :return: Utility of the agent
        """
        best_social_welfare = 0
        best_utility_me = 0

        for bid in self.preference.bids:
            my_utility = bid.utility
            opp_utility = estimated_preference.get_utility(bid)

            social_welfare = my_utility + opp_utility

            if social_welfare > best_social_welfare:
                best_social_welfare = social_welfare
                best_utility_me = my_utility

        return best_utility_me

    def determineDifference(self, senderInfo: OpponentInfo, first: BidDetails, second: BidDetails):
        return {issue: first.bid[issue] != second.bid[issue] for issue in self.preference.issues}

    def getOpponentInfoObjectOfSender(self, sender):
        if self.infoA is not None and self.infoA.agentID == sender:
            return self.infoA
        elif self.infoB is not None and self.infoB.agentID == sender:
            return self.infoA

        return None

    def initializeOpponentInfo(self, sender):
        if self.infoA is None:
            self.infoA = OpponentInfo(sender, self.preference)
        elif self.infoB is None:
            self.infoB = OpponentInfo(sender, self.preference)

        if self.infoA is not None and self.infoB is not None:
            self.initialized = True

    def updateOpponentBidHistory(self, opponent: OpponentInfo, bid: nenv.Bid, t: float):
        if opponent is None or bid is None:
            return

        opponent.agentBidHistory.add(BidDetails(bid, self.preference.get_utility(bid), t))

        for i, w in enumerate(opponent.bidPointWeights):
            if w > 1:
                opponent.bidPointWeights[i] -= 1

        opponent.bidPointWeights.append(self.maxWeightForBidPoint)

        if opponent.bestBid is None or self.preference.get_utility(bid) >= self.preference.get_utility(opponent.bestBid):
            opponent.bestBid = bid
            opponent.bestBids.add(BidDetails(bid, self.preference.get_utility(bid), t))
        else:
            opponent.bestBids.add(BidDetails(opponent.bestBid, self.preference.get_utility(opponent.bestBid), t))

