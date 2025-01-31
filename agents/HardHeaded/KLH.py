import math
import random
from typing import Tuple, List, Dict, Optional

import nenv
from agents.HardHeaded.BidHistory import BidHistory
from agents.HardHeaded.BidSelector import BidSelector


class HardHeaded(nenv.AbstractAgent):
    """
        **HardHeaded agent by Thijs van Krimpen**:
            As the name implies, the agent is hardheaded, it will not concede until the very end. Using a concession
            function, it generates bids in a monotonic way, which resets to a random value after the dynamic concession
            limit is reached. In practice, this means that most of the time the agent will cycle through the same range
            of bids. Since the preferences of the opponent are not known, the agent tries to learn the opponent’s
            preference profile. It chooses bids which it thinks are optimal for the opponent in case there are
            equivalent bids for itself. [Krimpen2013]_

        ANAC 2011 individual utility winner.

        .. [Krimpen2013] van Krimpen, T., Looije, D., Hajizadeh, S. (2013). HardHeaded. In: Ito, T., Zhang, M., Robu, V., Matsuo, T. (eds) Complex Automated Negotiations: Theories, Models, and Software Competitions. Studies in Computational Intelligence, vol 435. Springer, Berlin, Heidelberg. <https://doi.org/10.1007/978-3-642-30737-9_17>
    """

    bidHistory: BidHistory                                              #: BidHistory object to hold both agent and opponent history
    BSelector: BidSelector                                              #: BidSelector object
    MINIMUM_BID_UTILITY: float                                          #: Minimum bid utility to offer
    TOP_SELECTED_BIDS: int = 4                                          #: Maximum number of selected bids
    LEARNING_COEF: float = 0.2                                          #: Calculation for golden value in the opponent model
    LEARNING_VALUE_ADDITION: int = 1                                    #: Value count effect
    UTILITY_TOLERANCE: float = 0.01                                     #: Utility tolerance
    Ka: float                                                           #: Parameter to calculate concession step
    e: float                                                            #: Parameter to calculate concession step
    discountF: float                                                    #: Discount factor
    lowestYetUtility: float                                             #: Lowest utility that the agent made yet

    offerQueue: List[Tuple[float, nenv.Bid]]                            #: Offer queue
    opponentLastBid: Optional[nenv.Bid]                                 #: Last received bid
    firstRound: bool                                                    #: If it is first round, or not

    oppUtility: Optional[nenv.OpponentModel.EstimatedPreference]        #: Estimated preferences of the opponent
    numberOfIssues: int                                                 #: Number of issues in that domain

    valueCounter: Dict[nenv.Issue, Dict[str, float]]                    #: Value counter for Frequentist approach

    maxUtil: float                                                      #: Maximum possible utility in that domain
    minUtil: float                                                      #: Minimum utility to offer

    opponentbestbid: Optional[nenv.Bid]                                 #: Highest received bid
    opponentbestentry: Tuple[float, nenv.Bid]                           #: Entry of highest received bid

    random100: random.Random                                            #: Random object
    random200: random.Random                                            #: Random object
    round: int                                                          #: Current negotiation round

    def initiate(self, opponent_name: Optional[str]):
        # Default parameters and objects
        self.BSelector = BidSelector(self.preference)
        self.bidHistory = BidHistory(self.preference)
        self.MINIMUM_BID_UTILITY = 0.585
        self.Ka = 0.05
        self.e = 0.05
        self.discountF = 1.
        self.lowestYetUtility = 1.
        self.round = 0

        self.offerQueue = []
        self.opponentLastBid = None
        self.opponentbestbid = None
        self.firstRound = True
        self.numberOfIssues = len(self.preference.issues)
        self.oppUtility = None
        self.minUtil = self.MINIMUM_BID_UTILITY
        self.maxUtil = 1.

        # Highest bid for me
        keys = list(self.BSelector.BidList.keys())
        keys.sort()

        highestBid = self.BSelector.BidList[keys[-1]]

        self.maxUtil = self.preference.get_utility(highestBid)

        # Random objects
        self.random100 = random.Random()
        self.random200 = random.Random()

        # Initiate the opponent model
        self.oppUtility = nenv.OpponentModel.EstimatedPreference(self.preference)

        w = 1. / self.numberOfIssues

        self.valueCounter = {}

        for issue in self.oppUtility.issues:
            self.oppUtility[issue] = w
            self.valueCounter[issue] = {}

            for value in issue.values:
                self.oppUtility[issue, value] = 1.
                self.valueCounter[issue][value] = 1.

        # Update minimum bid utility depending on the reservation value
        self.MINIMUM_BID_UTILITY = max(self.MINIMUM_BID_UTILITY, self.preference.reservation_value)

    @property
    def name(self) -> str:
        return "HardHeaded"

    def floorEntry(self, d: dict, target_key: float) -> tuple:
        """
            It returns a key-value mapping associated with the greatest key less than or equal to the given key.
        :param d: Dictionary
        :param target_key: Target key
        :return: key-value pair
        """
        all_keys = list(d.keys())
        all_keys.sort(reverse=True)

        for i, key in enumerate(all_keys):
            if key <= target_key:
                return key, d[key]

        return all_keys[-1], d[all_keys[-1]]

    def lowerEntry(self, d: dict, target_key: float) -> tuple:
        """
            It returns a key-value mapping associated with the greatest key strictly less than the given key.
        :param d: Dictionary
        :param target_key: Target key
        :return: key-value pair
        """
        all_keys = list(d.keys())
        all_keys.sort(reverse=True)

        for i, key in enumerate(all_keys):
            if key < target_key:
                return key, d[key]

        return all_keys[-1], d[all_keys[-1]]

    def receive_offer(self, bid: nenv.Bid, t: float):
        opbestvalue: float

        # Update the opponent model
        self.opponentLastBid = bid.copy()
        self.bidHistory.opponentBids.append(bid)
        self.updateLearner()

        # Update the highest received bid
        if self.opponentbestbid is None:
            self.opponentbestbid = bid.copy()
        elif self.preference.get_utility(bid) > self.preference.get_utility(self.opponentbestbid):
            self.opponentbestbid = bid.copy()

        # Update opponent best entry
        opbestvalue = self.floorEntry(self.BSelector.BidList, self.preference.get_utility(self.opponentbestbid))[0]

        try_counter = 0

        # Try to find the entry
        while self.floorEntry(self.BSelector.BidList, opbestvalue)[1] != self.opponentbestbid and try_counter < 1000:
            opbestvalue = self.lowerEntry(self.BSelector.BidList, opbestvalue)[0]
            try_counter += 1

        self.opponentbestentry = self.floorEntry(self.BSelector.BidList, opbestvalue)

    def updateLearner(self):
        """
            This method updates the opponent model
        :return: Nothing
        """

        # There must be at least two received bids
        if len(self.bidHistory.opponentBids) < 2:
            return

        numberOfUnchanged = 0

        lastDiffSet = self.bidHistory.BidDifferenceofOpponentsLastTwo()

        # Counting the number of unchanged issues
        for i in lastDiffSet.keys():
            if lastDiffSet[i] == 0:
                numberOfUnchanged += 1

        '''
            This is the value to be added to weights of unchanged issues before normalization. Also the value that is 
            taken as the minimum possible weight, (therefore defining the maximum possible also).
        '''
        goldenValue = self.LEARNING_COEF / self.numberOfIssues
        # The total sum of weights before normalization.
        totalSum = 1. + goldenValue * numberOfUnchanged
        # The maximum possible weight
        maximumWeight = 1. - self.numberOfIssues * goldenValue / totalSum

        # re-weighting issues while making sure that the sum remains 1
        for i in lastDiffSet:
            if lastDiffSet[i] == 0 and self.oppUtility.get_issue_weight(i) < maximumWeight:
                self.oppUtility[i] = (self.oppUtility[i] + goldenValue) / totalSum
            else:
                self.oppUtility[i] = self.oppUtility[i] / totalSum

        # Update Estimated Preferences
        for issue in self.preference.issues:
            self.valueCounter[issue][self.opponentLastBid[issue]] = self.valueCounter[issue][self.opponentLastBid[issue]] + self.LEARNING_VALUE_ADDITION

            for value in issue.values:
                self.oppUtility[issue, value] = self.valueCounter[issue][value]

        self.oppUtility.normalize()

    def get_p(self, t: float) -> float:
        """
            This function calculates the concession amount based on remaining time, initial parameters, and, the
            discount factor.
        :param t: Current negotiation time
        :return: Concession step
        """
        time = t
        Fa: float = 0.
        p = 1.
        step_point = self.discountF
        tempMax = self.maxUtil
        tempMin = self.minUtil
        tempE = self.e
        ignoreDiscountThreshold = 0.9

        if step_point >= ignoreDiscountThreshold:
            Fa = self.Ka + (1 - self.Ka) * math.pow(time / step_point, 1. / self.e)
            p = self.minUtil + (1 - Fa) * (self.maxUtil - self.minUtil)
        elif time <= step_point:
            tempE = self.e / step_point
            Fa = self.Ka + (1 - self.Ka) * math.pow(time / step_point, 1. / tempE)
            tempMin += abs(tempMax - tempMin) * step_point
            p = tempMin + (1 - Fa) * (tempMax - tempMin)
        else:
            tempE = 30.
            Fa = (self.Ka + (1 - self.Ka) * math.pow((time - step_point) / (1 - step_point), 1. / tempE))
            tempMax = tempMin + abs(tempMax - tempMin) * step_point
            p = tempMin + (1 - Fa) * (tempMax - tempMin)

        return p

    def act(self, t: float) -> nenv.Action:
        """
        This is the main strategy of that determines the behavior of the agent. It uses a concession function that in
        accord with remaining time decides which bids should be offered. Also using the learned opponent utility, it
        tries to offer more acceptable bids.
        """
        self.round += 1

        newBid: Tuple[float, nenv.Bid]
        newAction = None
        p = self.get_p(t)

        if self.firstRound:
            # In the first round, offer the highest bid
            self.firstRound = not self.firstRound
            keys = list(self.BSelector.BidList.keys())
            keys.sort()

            newBid = (keys[-1], self.BSelector.BidList[keys[-1]])

            self.offerQueue.append(newBid)
        elif len(self.offerQueue) == 0 or self.offerQueue is None:
            # If the offers queue has yet bids to be offered, skip this.
            # Otherwise, select some new bids to be offered.
            self.offerQueue = []
            newBids = {}
            newBid = self.lowerEntry(self.BSelector.BidList, self.bidHistory.myBids[-1][0])
            newBids[newBid[0]] = newBid[1]

            if newBid[0] < p:
                indexer = self.random100.choice(list(range(len(self.bidHistory.myBids))))
                del newBids[newBid[0]]

                newBids[self.bidHistory.myBids[indexer][0]] = self.bidHistory.myBids[indexer][1]

            firstUtil = newBid[0]

            addBid = self.lowerEntry(self.BSelector.BidList, firstUtil)

            addUtil = addBid[0]
            count = 0

            while firstUtil - addUtil < self.UTILITY_TOLERANCE and addUtil >= p:
                newBids[addUtil] = addBid[1]
                addBid = self.lowerEntry(self.BSelector.BidList, addUtil)
                addUtil = addBid[0]
                count += 1

            # Adding selected bids to offering queue
            if len(newBids) <= self.TOP_SELECTED_BIDS:
                self.offerQueue.extend(newBids.items())
            else:
                addedSofar = 0
                bestBid = None

                while addedSofar <= self.TOP_SELECTED_BIDS:
                    keys = list(newBids.keys())
                    keys.sort()

                    bestBid = (keys[-1], newBids[keys[-1]])

                    # Select the best bid from the new bid list by considering estimated opponent utility.
                    for e in newBids:
                        if self.oppUtility.get_utility(newBids[e]) > self.oppUtility.get_utility(bestBid[1]):
                            bestBid = (e, newBids[e])

                    self.offerQueue.append(bestBid)
                    del newBids[bestBid[0]]
                    addedSofar += 1

            # If opponentbest entry is better for us then the offer queue
            # Then replace the top entry
            if self.offerQueue[0][0] < self.opponentbestentry[0]:
                self.offerQueue.insert(0, self.opponentbestentry)

        # If no bids are selected there must be a problem
        if len(self.offerQueue) == 0 or self.offerQueue is None:
            self.offerQueue = []

            bestBid1 = self.preference.get_random_bid()

            if self.opponentLastBid is not None and self.can_accept() and self.preference.get_utility(bestBid1) <= self.preference.get_utility(self.opponentLastBid):
                return self.accept_action
            elif self.can_accept() and bestBid1 is None:
                newAction = self.accept_action
            else:
                newAction = nenv.Offer(bestBid1)

                # Update lowestYetUtility
                if self.preference.get_utility(bestBid1) < self.lowestYetUtility:
                    self.lowestYetUtility = self.preference.get_utility(bestBid1)

        # If opponent's suggested bid is better than the one we just, accept it
        if self.opponentLastBid is not None and self.can_accept() and (self.preference.get_utility(self.opponentLastBid) > self.lowestYetUtility or self.preference.get_utility(self.offerQueue[0][1]) <= self.preference.get_utility(self.opponentLastBid)):
            return self.accept_action
        else:         # else offer a new bid
            offer = self.offerQueue.pop(0)

            self.bidHistory.myBids.append(offer)

            if offer[0] < self.lowestYetUtility:
                self.lowestYetUtility = self.preference.get_utility(offer[1])

            newAction = nenv.Offer(offer[1])

        return newAction
