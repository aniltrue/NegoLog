import random
from typing import List, Optional
import nenv
from agents.AgentGG.ImpMap import ImpMap


class AgentGG(nenv.AbstractAgent):
    """
        **AgentGG by Shaobo Xu**:
            AgentGG applies Frequentist opponent model to estimate both self and opponent preferences. So, it considers
            the importance of a bid instead of utility value. Besides, it randomly selects bid based on both estimated
            self and opponent preferences. It also applies Time-Based approach for the bidding strategy. [Aydogan2020]_

        ANAC 2019 individual utility category winner.

        .. [Aydogan2020] Aydoğan, R. et al. (2020). Challenges and Main Results of the Automated Negotiating Agents Competition (ANAC) 2019. In: Bassiliades, N., Chalkiadakis, G., de Jonge, D. (eds) Multi-Agent Systems and Agreement Technologies. EUMAS AT 2020 2020. Lecture Notes in Computer Science(), vol 12520. Springer, Cham. <https://doi.org/10.1007/978-3-030-66412-1_23>
    """
    impMap: ImpMap                          #: Opponent Model for self preferences
    opponentImpMap: ImpMap                  #: Opponent Model for opponent preferences
    offerLowerRatio: float                  #: Lower ratio for the offer range
    offerHigherRatio: float                 #: Higher ratio for the offer range
    MAX_IMPORTANCE: float                   #: Max. importance for self
    MIN_IMPORTANCE: float                   #: Min. importance for self
    MEDIAN_IMPORTANCE: float                #: Median importance for self
    MAX_IMPORTANCE_BID: nenv.Bid            #: The bid content which is max. importance
    MIN_IMPORTANCE_BID: nenv.Bid            #: The bid content which is min. importance
    OPPONENT_MAX_IMPORTANCE: float          #: Max. importance of opponent
    OPPONENT_MIN_IMPORTANCE: float          #: Min. importance of opponent
    receivedBid: nenv.Bid                   #: Received bid
    initialOpponentBid: nenv.Bid            #: First received bid
    reservationImportanceRatio: float       #: Normalized reservation value
    offerRandomly: bool                     #: Select random bid when t < 0.2

    startTime: float                        #: The negotiation time when the first bid is received
    maxOppoBidImpForMeGot: bool             #: If max. received bid is determined
    maxOppoBidImpForMe: float               #: Max. received bid
    estimatedNashPoint: float               #: Estimated nash point
    lastReceivedBid: nenv.Bid               #: Last received bid
    initialTimePass: bool                   #: If the first bid is received, or not

    def initiate(self, opponent_name: Optional[str]):
        # Default values
        self.offerLowerRatio = 1.0
        self.offerHigherRatio = 1.1
        self.offerRandomly = True
        self.maxOppoBidImpForMeGot = False
        self.initialTimePass = False
        self.maxOppoBidImpForMe = 0.
        self.estimatedNashPoint = 0.

        self.reservationImportanceRatio = self.preference.reservation_value

        # Initiate opponent models

        self.impMap = ImpMap(self.preference)
        self.opponentImpMap = ImpMap(self.preference)

        self.impMap.self_update(self.preference.bids)

        # Find Max, Min and Median bids for me

        self.getMaxAndMinBid()
        self.getMedianBid()

    def act(self, t: float) -> nenv.Action:
        # If it is in first round, offer the highest bid.
        if not self.can_accept():
            return nenv.Offer(self.MAX_IMPORTANCE_BID)

        # Get estimated importance for me
        impRatioForMe = (self.impMap.getImportance(self.receivedBid) - self.MIN_IMPORTANCE) / (self.MAX_IMPORTANCE - self.MIN_IMPORTANCE)

        # Check acceptance condition
        if impRatioForMe >= self.offerLowerRatio:
            return self.accept_action

        # If it is first received.
        if not self.maxOppoBidImpForMeGot:
            self.getMaxOppoBidImpForMe(t, 3. / 1000.0)

        # Update opponent model when t < 0.3
        if t < 0.3:
            self.opponentImpMap.opponent_update(self.receivedBid)

        # Update thresholds based on the current negotiation time
        self.getThreshold(t)

        # Near to deadline, check additional acceptance condition.
        if t >= 0.9989:
            if impRatioForMe > self.reservationImportanceRatio + 0.2:
                return self.accept_action

        # Randomly selects the bid that will be offered
        bid = self.getNeededRandomBid(self.offerLowerRatio, self.offerHigherRatio)

        self.lastReceivedBid = self.receivedBid

        return nenv.Offer(bid)

    def receive_offer(self, bid: nenv.Bid, t: float):
        # Set received bic
        self.receivedBid = bid

    @property
    def name(self) -> str:
        return "AgentGG"

    def getMaxOppoBidImpForMe(self, time: float, timeLast: float):
        """
            This method finds the highest received importance.
        :param time: Current negotiation time
        :param timeLast: Last negotiation time
        :return: Nothing
        """
        thisBidImp = self.impMap.getImportance(self.receivedBid)    # Normalized importance

        if thisBidImp > self.maxOppoBidImpForMe:  # Update the maximum received.

            self.maxOppoBidImpForMe = thisBidImp

        if self.initialTimePass:
            if time - self.startTime > timeLast:
                # Normalized importance
                maxOppoBidRatioForMe = (self.maxOppoBidImpForMe - self.MIN_IMPORTANCE) / (self.MAX_IMPORTANCE - self.MIN_IMPORTANCE)

                self.estimatedNashPoint = (1 - maxOppoBidRatioForMe) / 1.7 + maxOppoBidRatioForMe

                self.maxOppoBidImpForMeGot = True
            elif self.lastReceivedBid != self.receivedBid:  # If it is the first received bid.
                self.initialTimePass = True
                self.startTime = time

    def getThreshold(self, time: float):
        """
            This method decides the corresponding thresholds based on the current negotiation time.
        :param time: Current negotiation time
        :return: Nothing
        """
        if time < 0.01:
            self.offerLowerRatio = 0.9999
        elif time < 0.02:
            self.offerLowerRatio = 0.99
        elif time < 0.2:
            self.offerLowerRatio = 0.99 - 0.5 * (time - 0.02)
        elif time < 0.5:
            self.offerRandomly = False
            p2 = 0.3 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            self.offerLowerRatio = 0.9 - (0.9 - p2) / (0.5 - 0.2) * (time - 0.2)
        elif time < 0.9:
            p1 = 0.15 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            p2 = 0.05 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            possibleRatio = p1 - (p1 - p2) / (0.98 - 0.9) * (time - 0.9)
            self.offerLowerRatio = max(possibleRatio, self.reservationImportanceRatio + 0.3)
        elif time < 0.995:
            p1 = 0.05 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            p2 = 0.0 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            possibleRatio = p1 - (p1 - p2) / (0.995 - 0.98) * (time - 0.98)

            self.offerLowerRatio = max(possibleRatio, self.reservationImportanceRatio + 0.25)
        elif time < 0.999:
            p1 = 0.0 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            p2 = -0.35 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            possibleRatio = p1 - (p1 - p2) / (0.9989 - 0.995) * (time - 0.995)
            self.offerLowerRatio = max(possibleRatio, self.reservationImportanceRatio + 0.25)
        else:
            possibleRatio = -0.4 * (1 - self.estimatedNashPoint) + self.estimatedNashPoint
            self.offerLowerRatio = max(possibleRatio, self.reservationImportanceRatio + 0.2)

        self.offerHigherRatio = self.offerLowerRatio + 0.1

    def getReservationRatio(self) -> float:
        """
            This method calculates the normalized reservation value
        :return: Normalized reservation value
        """
        medianBidRatio = (self.MEDIAN_IMPORTANCE - self.MIN_IMPORTANCE) / (self.MAX_IMPORTANCE - self.MIN_IMPORTANCE)

        return self.preference.reservation_value * medianBidRatio / 0.5

    def getMaxAndMinBid(self):
        """
            This method finds the highest and lowest normalized importance for self
        :return: Nothing
        """
        lValues1 = {}   # Highest bid content
        lValues2 = {}   # Lowest bid content

        for issue, impUnitList in self.impMap.map.items():
            value1 = impUnitList[0].valueOfIssue
            value2 = impUnitList[-1].valueOfIssue

            lValues1[issue] = value1
            lValues2[issue] = value2

        self.MAX_IMPORTANCE_BID = nenv.Bid(lValues1)
        self.MIN_IMPORTANCE_BID = nenv.Bid(lValues2)
        self.MAX_IMPORTANCE = self.impMap.getImportance(self.MAX_IMPORTANCE_BID)
        self.MIN_IMPORTANCE = self.impMap.getImportance(self.MIN_IMPORTANCE_BID)

    def getMedianBid(self):
        """
            This method finds the median normalized importance for self
        :return: Nothing
        """
        median = (len(self.preference.bids) - 1) // 2
        median2 = -1

        if len(self.preference.bids) % 2 == 0:
            median2 = median + 1

        current = 0

        for bid in self.preference.bids:
            current += 1

            if current == median:
                self.MEDIAN_IMPORTANCE = self.impMap.getImportance(bid)

                if median2 == -1:
                    break

            if current == median2:
                self.MEDIAN_IMPORTANCE = self.impMap.getImportance(bid)
                break

        if median2 != -1:
            self.MEDIAN_IMPORTANCE /= 2

    def getNeededRandomBid(self, lowerRatio: float, upperRatio: float) -> nenv.Bid:
        """
            This method randomly selects a bid in a range to offer. This operation is also take the estimated
            preferences of the opponent in account.
        :param lowerRatio: Lower ratio for the range
        :param upperRatio: Upper ratio for the range
        :return: Randomly selected bid
        """

        # Range
        lowerThreshold = lowerRatio * (self.MAX_IMPORTANCE - self.MIN_IMPORTANCE) + self.MIN_IMPORTANCE
        upperThreshold = upperRatio * (self.MAX_IMPORTANCE - self.MIN_IMPORTANCE) + self.MIN_IMPORTANCE

        bids = self.get_bids(upperThreshold, lowerThreshold)

        for t in range(3):  # Try three time
            k = len(bids) * 2
            highest_opponent_importance = 0.

            returnedBid = None

            for i in range(k):
                bid = random.choice(bids)

                bidOpponentImportance = self.opponentImpMap.getImportance(bid)

                if self.offerRandomly:  # Randomly bid for the first 0.2 time
                    return bid

                # Check the estimated opponent importance to offer the highest observed one.
                if bidOpponentImportance > highest_opponent_importance:
                    highest_opponent_importance = bidOpponentImportance
                    returnedBid = bid

            # If no bid can be found.
            if returnedBid is not None:
                return returnedBid

        '''
        # Old code can be stuck.

        while True:
            bid = self.preference.get_random_bid()

            if self.impMap.getImportance(bid) >= lowerThreshold:
                return bid

        '''

        return self.get_random_bid(lowerThreshold)

    def get_random_bid(self, lower_threshold: float) -> nenv.Bid:
        """
            This method randomly selects a bid which has higher estimated importance than the given lower threshold.
        :param lower_threshold: Lower threshold
        :return: Random selected bid
        """
        bids = [bid for bid in self.preference.bids if self.impMap.getImportance(bid) >= lower_threshold]

        # If no bid >= lower_threshold
        if len(bids) == 0:
            return self.preference.get_random_bid(self.offerLowerRatio)

        rnd = random.Random()

        return rnd.choice(bids)

    def get_bids(self, upper_threshold: float, lower_threshold: float) -> List[nenv.Bid]:
        """
            This method selects the bids in given importance range.
        :param upper_threshold: Upper threshold
        :param lower_threshold: Lower threshold
        :return: List of bids
        """

        bids = [bid for bid in self.preference.bids if upper_threshold >= self.impMap.getImportance(bid) >= lower_threshold]

        return bids
