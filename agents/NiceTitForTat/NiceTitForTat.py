import math
import random
from typing import Optional
import nenv
from nenv import Action, Bid
from agents.NiceTitForTat.helpers.BidHistory import BidHistory, BidDetails
from nenv.OpponentModel import BayesianOpponentModel


class NiceTitForTat(nenv.AbstractAgent):
    """
        **NiceTitForTat agent by Tim Baarslag**:
            The Nice Tit for Tat agent plays a tit for tat strategy with respect to its own utility.
            The agent will initially cooperate, then respond in kind to the opponent’s previous
            action, while aiming for the Nash point of the negotiation scenario. After each move
            by the opponent, it updates its Bayesian opponent model to make sure it responds
            with a nice move to a concession by the opponent. [Baarslag2013]_

        .. [Baarslag2013] Tim Baarslag, Koen Hindriks, and Catholijn Jonker. A tit for tat negotiation strategy for real-time bilateral negotiations. Studies in Computational Intelligence, 435:229–233, 2013.

    """
    TIME_USED_TO_DETERMINE_OPPONENT_STARTING_POINT: float = 0.01
    NASH_POINT_UPDATE_RATE = 0.5
    myHistory: BidHistory
    opponentHistory: BidHistory
    offeredOpponentBestBid: int
    myNashUtility: float
    initialGap: float
    random100: random.Random
    opponent_model: BayesianOpponentModel

    @property
    def name(self) -> str:
        return "NiceTitForTat"

    def initiate(self, opponent_name: Optional[str]):
        self.myHistory = BidHistory()
        self.opponentHistory = BidHistory()
        self.random100 = random.Random()
        self.offeredOpponentBestBid = 0
        self.myNashUtility = 0.
        self.initialGap = 0.
        self.opponent_model = BayesianOpponentModel(self.preference)

    def receive_offer(self, bid: Bid, t: float):
        self.opponent_model.update(bid, t)
        self.opponentHistory.add(BidDetails(bid, self.preference.get_utility(bid), t))

    def act(self, t: float) -> Action:
        opening_bid = self.chooseOpeningBid()

        if len(self.last_received_bids) == 0:
            self.myHistory.add(BidDetails(opening_bid, opening_bid.utility, t))
            return nenv.Offer(opening_bid)

        if len(self.myHistory.history) == 0:
            self.myHistory.history.append(BidDetails(opening_bid, opening_bid.utility, t))
            return nenv.Offer(opening_bid)

        counter_bid = self.chooseCounterBid(t)

        if self.isAcceptable(counter_bid, t) and self.can_accept():
            return self.makeAcceptAction(t)

        self.myHistory.history.append(BidDetails(counter_bid, self.get_utility(counter_bid), t))

        return nenv.Offer(counter_bid)

    def get_utility(self, b: nenv.Bid) -> float:
        if b is None:
            return 0.

        return self.preference.get_utility(b)

    def chooseCounterBid(self, t: float):
        opponent_last_bid = self.opponentHistory.history[-1].bid if len(self.opponentHistory.history) else None

        if self.canUpdateBeliefs(t) and (
                self.random100.random() < self.NASH_POINT_UPDATE_RATE or self.myNashUtility == 0.):
            self.update_my_nash_utility()

        my_utility_of_opponent_last_bid = self.get_utility(opponent_last_bid)
        maximum_offered_utility_by_opponent = self.opponentHistory.getMaximumUtility()
        minimum_offered_utility_by_opponent = self.opponentHistory.getMinumumUtility()
        min_utility_of_opponent_first_bids = self.getMinimumUtilityOfOpponentFirstBids(my_utility_of_opponent_last_bid)

        opponent_concession = maximum_offered_utility_by_opponent - min_utility_of_opponent_first_bids

        denominator = self.myNashUtility - min_utility_of_opponent_first_bids
        if denominator == 0:
            opponent_concede_factor = 0.0
        else:
            opponent_concede_factor = min(1, opponent_concession / denominator)

        my_concession = opponent_concede_factor * (1 - self.myNashUtility)
        my_current_target_utility = 1. - my_concession

        self.initialGap = 1 - min_utility_of_opponent_first_bids
        gap_to_nash = max(0., my_current_target_utility - self.myNashUtility)

        bonus = self.get_bonus(t)
        tit = bonus * gap_to_nash
        my_current_target_utility -= tit

        myBids = self.getBidsOfUtility(my_current_target_utility)
        my_bid = self.getBestBidForOpponent(myBids)

        my_bid = self.makeAppropriate(my_bid)

        return my_bid

    def canUpdateBeliefs(self, t: float):
        if t > 0.99:
            return False

        if self.domain_size > 10000:
            if t > 0.5:
                return False

        return True

    def get_bonus(self, t: float) -> float:
        discount_factor = 1.0
        discount_bonus = 0.5 - 0.4 * discount_factor

        is_bid_domain = self.domain_size > 3000
        time_bonus = 0.

        minTime = 0.91

        if is_bid_domain:
            minTime = 0.85

        if t > minTime:
            time_bonus = min(1., 20 * (t - minTime))

        bonus = max(discount_bonus, time_bonus)

        return min(1., max(0., bonus))

    def update_my_nash_utility(self):
        self.myNashUtility = 0.7

        nash_multipler = self.get_nash_multiplier(self.initialGap)

        if self.domain_size < 200000:
            self.myNashUtility = self.get_estimated_nash_utility()

        self.myNashUtility *= nash_multipler

        self.myNashUtility = min(1., max(0.5, self.myNashUtility))

    def get_estimated_nash_utility(self) -> float:
        """
            This method finds the utility of the agent where the estimated Nash product is maximum.
        :return: The utility of the agent
        """
        best_nash_product = 0.
        best_utility_me = 0.

        opp_preference = self.opponent_model.preference

        for bid in self.preference.bids:
            utility_me = bid.utility
            utility_opp = opp_preference.get_utility(bid)

            nash_product = utility_opp * utility_me

            if nash_product > best_nash_product:
                best_nash_product = nash_product
                best_utility_me = utility_me

        return best_utility_me

    def get_nash_multiplier(self, gap: float):
        mult = 1.4 - 0.6 * gap

        return max(0., mult)

    def getMinimumUtilityOfOpponentFirstBids(self, myUtilityOfOpponentLastBid: float):
        firstBids = self.opponentHistory.filterBetweenTime(0, self.TIME_USED_TO_DETERMINE_OPPONENT_STARTING_POINT)

        first_bids_min_utility = 0.

        if len(firstBids.history) == 0:
            first_bids_min_utility = self.opponentHistory.history[0].utility
        else:
            first_bids_min_utility = firstBids.getMinumumUtility()

        return first_bids_min_utility

    def makeAppropriate(self, myPlannedBid: nenv.Bid):
        bestBidByOpponent = self.opponentHistory.getBestBidDetails().bid

        bestUtilityByOpponent = self.get_utility(bestBidByOpponent)
        myPlannedUtility = self.get_utility(myPlannedBid)

        if bestUtilityByOpponent >= myPlannedUtility:
            return bestBidByOpponent

        return myPlannedBid

    def chooseOpeningBid(self):
        return self.preference.bids[0]

    def isAcceptable(self, plannedBid: nenv.Bid, t: float):
        opponent_last_bid = self.opponentHistory.history[-1].bid if len(self.opponentHistory.history) else None
        my_next_bid = plannedBid

        if self.get_utility(opponent_last_bid) >= self.get_utility(my_next_bid):
            return True

        if t < 0.98:
            return False

        offered_utility = self.get_utility(opponent_last_bid)
        time_left = 1 - t

        recent_bids = self.opponentHistory.filterBetweenTime(t - time_left, t)
        recent_bid_size = len(recent_bids.history)

        enough_bids_to_come = 10

        if self.domain_size > 10000:
            enough_bids_to_come = 40

        if recent_bid_size > enough_bids_to_come:
            return False

        window = time_left
        recent_better_bids = self.opponentHistory.filterBetween(offered_utility, 1, t - window, t)
        n = len(recent_better_bids.history)

        if window == 0:
            p = 1.0
        else:
            p = time_left / window

        if p > 1:
            p = 1

        pAllMiss = math.pow(1 - p, n)

        if n == 0:
            pAllMiss = 1

        pAtLeastOneHit = 1 - pAllMiss
        avg = recent_better_bids.getAverageUtility()
        expected_util_of_waiting_for_a_better_bid = pAtLeastOneHit * avg

        if offered_utility > expected_util_of_waiting_for_a_better_bid:
            return True

        return False

    def makeAcceptAction(self, t: float):
        opponent_last_bid = self.opponentHistory.history[-1].bid if len(self.opponentHistory.history) else None
        offered_utility = self.get_utility(opponent_last_bid)

        time_left = 1 - t
        recent_bids = self.opponentHistory.filterBetweenTime(t - time_left, t)
        best_bid = self.opponentHistory.getBestBidDetails().bid
        best_bid_utility = self.get_utility(best_bid)

        if len(recent_bids.history) > 1 and best_bid_utility > offered_utility and self.offeredOpponentBestBid <= 3:
            self.offeredOpponentBestBid += 1

            return nenv.Offer(best_bid)

        return self.accept_action

    def getBidsOfUtilityRange(self, lowerBound: float, upperBound: float):
        limit = 2

        bids_in_range = []

        for bid in self.preference.bids:
            util = bid.utility

            if lowerBound <= util <= upperBound:
                bids_in_range.append(bid)

            if self.domain_size > 10000 and len(bids_in_range) >= limit:
                return bids_in_range

        return bids_in_range

    def getBidsOfUtility(self, target: float):
        if target > 1:
            target = 1

        min = target * 0.98
        max = target + 0.04

        max += 0.01
        bids = self.getBidsOfUtilityRange(min, max)
        size = len(bids)

        if size > 1 or (max >= 1 and size > 0):
            return bids

        while max <= 1:
            max += 0.01
            bids = self.getBidsOfUtilityRange(min, max)
            size = len(bids)

            if size > 1 or (max >= 1 and size > 0):
                return bids

        return [self.chooseOpeningBid()]

    def getBestBidForOpponent(self, bids: list) -> nenv.Bid:
        possibleBidHistory = BidHistory()

        for b in bids:
            utility = self.opponent_model.preference.get_utility(b)
            possibleBidHistory.add(BidDetails(b, utility, 0.))

        n = int(round(len(bids) / 10.))

        if n < 3:
            n = 3

        if n > 20:
            n = 20

        bestN = possibleBidHistory.getBestBidHistory(n)
        randomBestN = bestN.getRandom(self.random100)

        return randomBestN.bid

    @property
    def domain_size(self) -> int:
        return len(self.preference.bids)
