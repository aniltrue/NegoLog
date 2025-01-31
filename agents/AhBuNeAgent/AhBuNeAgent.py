import math
import random
from typing import List, Optional
import nenv
from agents.AhBuNeAgent.impmap.SimilarityMap import SimilarityMap
from agents.AhBuNeAgent.impmap.OppSimilarityMap import OppSimilarityMap
from agents.AhBuNeAgent.linearorder.SimpleLinearOrdering import SimpleLinearOrdering
from agents.AhBuNeAgent.linearorder.OppSimpleLinearOrdering import OppSimpleLinearOrderding
from nenv import Action, Bid, Offer


class AhBuNeAgent(nenv.AbstractAgent):
    """
        **AhBuNeAgent by Ahmet Burak Yıldırım**:
            The proposed heuristic-based bidding strategy checks whether it has sufficient orderings to reason about its
            complete preferences and accordingly decides whether to sacrifice some utility in return for preference
            elicitation. While making an offer, it uses the most-desired known outcome as a reference and modifies the
            content of the bid by adopting a concession-based strategy. By analyzing the content of the given ordered
            bids, the importance ranking of the issues is estimated. As our agent adopts a fixed time-based concession
            strategy and takes the estimated issue importance ranks into account, it determines to what extent the
            issues are to be modified. The evaluation results of the ANAC 2020 show that our agent beats the other
            participating agents in terms of the received individual score.

            Importance Map opponent model which is a Frequentist approach is implemented to estimate both self and
            opponent preferences. Importance Map decides the worst (i.e., forbidden) and best (i.e., available) values
            to make a safe offers. [Yildirim2023]_

        ANAC 2020 individual utility category winner.

        .. [Yildirim2023] Yıldırım, A.B., Sunman, N., Aydoğan, R. (2023). AhBuNe Agent: Winner of the Eleventh International Automated Negotiating Agent Competition (ANAC 2020). In: Hadfi, R., Aydoğan, R., Ito, T., Arisaka, R. (eds) Recent Advances in Agent-Based Negotiation: Applications and Competition Challenges. IJCAI 2022. Studies in Computational Intelligence, vol 1092. Springer, Singapore. <https://doi.org/10.1007/978-981-99-0561-4_6>
    """
    rnd: random.Random                                      #: Random object
    ourNumFirstBids: int                                    #: Our number of first bids
    ourNumLastBids: int                                     #: Our number of last bids
    oppNumFirstBids: int                                    #: Opponent's number of first bids
    ourKnownBidNum: int                                     #: Our number of known bids
    oppKnownBidNum: int                                     #: Opponent's number of known bids

    time: float                                             #: Time
    allPossibleBids: List[nenv.Bid]                         #: List of all possible bids
    allPossibleBidsSize: int                                #: Length of the list of all possible bids

    ourLinearPartialOrdering: SimpleLinearOrdering          #: Our estimated profile
    oppLinearPartialOrdering: OppSimpleLinearOrderding      #: Opponent's estimated profile
    ourSimilarityMap: SimilarityMap                         #: Our Similarity Map
    oppSimilarityMap: OppSimilarityMap                      #: Opponent's Similarity Map

    lastReceivedBid: Optional[nenv.Bid]                     #: Last received bid
    utilityLowerBound: float                                #: Lower utility bound
    ourMaxCompromise: float                                 #: Our max. compromise

    lostElicityScore: float                                 #: The lost of elicity score
    elicitationCost: float                                  #: Elicitation cost
    maxElicitationLost: float                               #: Maximum lost of elicity
    leftElicitationNumber: int                              #: Number of not elicitated
    elicitationBid: Optional[nenv.Bid]                      #: Elicitated bid of the agent
    mostCompromisedBids: list                               #: List of most compromised bids
    oppElicitatedBid: List[nenv.Bid]                        #: Elicitated bid of the opponent
    reservationBid: nenv.Bid                                #: Reservation bid

    @property
    def name(self) -> str:
        return "AhBuNe"

    def initiate(self, opponent_name: Optional[str]):
        # Default values
        self.ourKnownBidNum = 0
        self.oppKnownBidNum = 0
        self.time = 0.

        self.lastReceivedBid = None
        self.utilityLowerBound = 1.
        self.ourMaxCompromise = 0.1

        self.lostElicityScore = 0.
        self.elicitationCost = 0.01
        self.maxElicitationLost = 0.05
        self.leftElicitationNumber = 0
        self.elicitationBid = None

        self.mostCompromisedBids = []
        self.oppElicitatedBid = []

        self.allPossibleBids = self.preference.bids
        self.allPossibleBidsSize = len(self.allPossibleBids)

        # Estimate our preferences
        self.ourLinearPartialOrdering = SimpleLinearOrdering(self.preference, list(reversed(self.allPossibleBids.copy())))
        self.oppLinearPartialOrdering = OppSimpleLinearOrderding()

        # Initiate opponent modelling
        self.ourSimilarityMap = SimilarityMap(self.preference)
        self.oppSimilarityMap = OppSimilarityMap(self.preference)

        self.ourSimilarityMap.update(self.ourLinearPartialOrdering)

    def receive_offer(self, bid: Bid, t: float):
        # Update last received bid
        self.lastReceivedBid = bid

    def selectAction(self, t: float) -> nenv.Action:
        """
            Determine an action that the agent makes
        :param t: Current negotiation time
        :return: Decided action
        """
        if self.lastReceivedBid is None:
            return self.makeAnOffer(t)

        if self.can_accept() and self.doWeAccept(self.lastReceivedBid, t):
            return self.accept_action

        return self.makeAnOffer(t)

    def act(self, t: float) -> Action:
        # Call strategySelection method
        self.strategySelection(t)
        action = self.selectAction(t)

        return action

    def makeAnOffer(self, t: float) -> Offer:
        """
            This method decides on an offer to make
        :param t: Current negotiation time
        :return: Decided offer
        """
        # If the deadline is near
        if t > 0.96:
            for i in reversed(range(self.ourLinearPartialOrdering.getKnownBidSize())):
                testBid = self.ourLinearPartialOrdering.getBidByIndex(i)

                if testBid in self.oppElicitatedBid and self.doWeAccept(testBid, t):
                    self.calculateBidUtility(testBid)

                    return Offer(testBid)

        oppMaxBid = self.oppLinearPartialOrdering.getMaxBid()

        ourOffer = self.ourSimilarityMap.findBidCompatibleWithSimilarity(self.utilityLowerBound, oppMaxBid)

        # If the current negotiation time <= 0.015
        if t < 0.015:
            # If we have more than 5 bids received
            if self.oppLinearPartialOrdering.isAvailable():
                count = 0

                # Limit
                while count < 500 and not self.oppSimilarityMap.isCompromised(ourOffer, self.oppNumFirstBids, 0.85) and self.ourLinearPartialOrdering.getMaxBid() == ourOffer:
                    ourOffer = self.ourSimilarityMap.findBidCompatibleWithSimilarity(0.85, oppMaxBid)
                    count += 1
            else:
                count = 0

                # Limit
                while count < 500 and ourOffer == self.ourLinearPartialOrdering.getMaxBid():
                    ourOffer = self.ourSimilarityMap.findBidCompatibleWithSimilarity(0.85, oppMaxBid)

                    count += 1

        # If we have more than one received bid
        elif self.lastReceivedBid is not None:
            if self.ourSimilarityMap.isCompatibleWithSimilarity(self.lastReceivedBid, 0.9):
                return Offer(self.lastReceivedBid)  # Offer the same
            if self.ourSimilarityMap.isCompatibleWithSimilarity(oppMaxBid, 0.9):
                return Offer(oppMaxBid)     # Offer the maximum important value for the opponent

            # Limit
            count = 0
            while count < 500 and self.oppLinearPartialOrdering.isAvailable() and not self.oppSimilarityMap.isCompromised(ourOffer, self.oppNumFirstBids, self.utilityLowerBound):
                ourOffer = self.ourSimilarityMap.findBidCompatibleWithSimilarity(self.utilityLowerBound, oppMaxBid)
                count += 1

        self.calculateBidUtility(ourOffer)

        return Offer(ourOffer)

    def doWeAccept(self, bid: nenv.Bid, t: float) -> bool:
        """
            This method check the acceptance condition based on the utility of received bid (Acceptance Strategy)
        :param bid: Received bid
        :param t: Current negotiation time
        :return: Acceptance, or not
        """
        # If the received bid is compatible
        if self.ourSimilarityMap.isCompatibleWithSimilarity(bid, 0.9):
            return True

        startUtilitySearch = self.utilityLowerBound

        # If the deadline is near
        if t >= 0.98:
            startUtilitySearch = self.utilityLowerBound - self.ourMaxCompromise

        # If opponent model is ready, use it to check acceptance condition
        if self.oppLinearPartialOrdering.isAvailable():
            for i in range(int(startUtilitySearch * 100), 96, 5):
                utilityTest = i / 100.

                # If received bid is compromised
                if self.oppSimilarityMap.isCompromised(bid, self.oppNumFirstBids, utilityTest):
                    # If received bid is compatible
                    if self.ourSimilarityMap.isCompatibleWithSimilarity(bid, utilityTest):
                        return True

                    break

        return False

    def strategySelection(self, t: float):
        """
            This method updates the Similarity Map of the opponent and First and Last number of bids
        :param t: Current negotiation time
        :return: Nothing
        """
        # Get number of known bids from the Similarity Maps
        self.utilityLowerBound = self.getUtilityLowerBound(t, self.lostElicityScore)
        self.ourKnownBidNum = self.ourLinearPartialOrdering.getKnownBidSize()
        self.oppKnownBidNum = self.oppLinearPartialOrdering.getKnownBidSize()

        # Update the first and last number of bids for us
        self.ourNumFirstBids = self.getNumFirst(self.utilityLowerBound, self.ourKnownBidNum)
        self.ourNumLastBids = self.getNumLast(self.utilityLowerBound, self.getUtilityLowerBound(1., self.lostElicityScore), self.ourKnownBidNum)

        self.ourSimilarityMap.createConditionLists(self.ourNumFirstBids, self.ourNumLastBids)

        # If there is a received bid, update the opponent model
        if self.lastReceivedBid is not None:
            self.oppLinearPartialOrdering.updateBid(self.lastReceivedBid)
            self.oppSimilarityMap.update(self.oppLinearPartialOrdering)
            # Update the first number of bids for the opponent
            self.oppNumFirstBids = self.getOppNumFist(self.utilityLowerBound, self.oppKnownBidNum)

    def getUtilityLowerBound(self, t: float, lostElicitScore: float) -> float:
        """
            This method provides the lower utility bound based on the curret negotiation time.
        :param t: Current negotiation time
        :param lostElicitScore: Lost of elicitation score
        :return: Lower utility bound
        """
        if t < 0.5:
            return -math.pow(t - 0.25, 2) + 0.9 + lostElicitScore
        elif t < 0.7:
            return -math.pow(1.5 * (t - 0.7), 2) + 0.9 + lostElicitScore

        return (3.25 * t * t) - (6.155 * t) + 3.6015 + lostElicitScore

    def getNumFirst(self, utilityLowerBound: float, knownBidNum: int) -> int:
        """
            This method provides the number of first (i.e., best) bids
        :param utilityLowerBound: Lower utility bound
        :param knownBidNum: Number of known bids
        :return: Number of first bids
        """
        return int(knownBidNum * (1 - utilityLowerBound) + 1)

    def getNumLast(self, utilityLowerBound: float, minUtilityLowerBound: float, knownBidNum: int) -> int:
        """
            This method provides the number of last (i.e., worst) bids
        :param utilityLowerBound: Lower utility bound
        :param minUtilityLowerBound: Minimum lower utility bound
        :param knownBidNum: Number of known bids
        :return: Number of last bids
        """
        return int(knownBidNum * (1 - minUtilityLowerBound)) - int(knownBidNum * (1 - utilityLowerBound) + 1)

    def getOppNumFist(self, utilityLowerBound: float, knownBidNum: int) -> int:
        """
            This method provides the number of first (i.e., best) bids for the opponent
        :param utilityLowerBound: Lower utility bound
        :param knownBidNum: Number of known bids
        :return: Number of first bids
        """
        return int(knownBidNum * (1 - utilityLowerBound) + 1)

    def calculateBidUtility(self, bid: nenv.Bid) -> float:
        """
            This method calculates the real utility of the given bid
        :param bid: Target bid
        :return: Utility value of the bid
        """
        return self.preference.get_utility(bid)
