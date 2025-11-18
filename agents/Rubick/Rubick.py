import math
import random
from typing import List, Dict, Optional
import nenv


class Rubick(nenv.AbstractAgent):
    """
        **Rubick by Okan Tunalı**:
            Rubick Agent is a complex time-based conceder enriched by derivations of well studied heuristics in
            automated negotiation field. The main component of the agent is the target utility, which is actually
            lower boundary in the bid generation and in acceptance condition. If the history is not available yet,
            target utility is initialized as the utility of the first received bid and updated to the highest utility
            received from any of the opponent parties. On the other hand, if it detects a negotiation history with the
            same opponents, it sets the lower bound to be the highest utility ever received throughout the negotiation;
            thinking that the opponents will be designed in a myopic way. Both bid generation and acceptance strategies
            include randomness; they follow a *Boulware* strategy but the pace of concession is randomized. Technically,
            they sample from one-sided Gaussian distributions whose standard deviation increase over time, increasing
            the likelihood of sending bids close to lower boundary. The opponent model resolves the bids into issue
            evaluation values and considering their occurrence frequencies, searches forbids that holds the target
            utility requirements while having the most common values. That is, it employs a frequency-based opponent
            modeling. Finally, the model keeps a list of bids accepted by only one of the opponents in the previous
            negotiations, which is sorted according to the gained utility by the Rubick agent. Elements of this list
            is used in bid generation only if there is almost no time left. [Aydogan2021]_

        ANAC 2017 individual utility category finalist.

        .. [Aydogan2021] Reyhan Aydoğan, Katsuhide Fujita, Tim Baarslag, Catholijn M. Jonker, and Takayuki Ito. ANAC 2017: Repeated multilateral negotiation league. In Advances in Auto- mated Negotiations, pages 101–115, Singapore, 2021. Springer Singapore.
    """
    lastReceivedBid: nenv.Bid  # Last received bid
    history: List[nenv.Bid]  # Negotiation history of the previous negotiation session
    parties: List[str]  # List of part names
    histOpp0: List[List[float]]  # History of opponent0
    histOpp1: List[List[float]]  # History of opponent1
    isHistoryAnalyzed: bool  # Check if the previous history is analyzed, or not
    numberOfReceivedOffer: int  # The number of received bids
    profileOrder: List[int]  # List of party ids
    opponentNames: List[str]  # List of opponent names
    acceptanceLimits: List[float]  # Decided acceptance limits
    maxReceivedBidutil: float  # Maximum utility of the received bid
    lastpartyname: str  # The name of last opponent
    bestAcceptedBids: List[nenv.Bid]  # List of best accepted bids
    threshold: float  # Reservation value

    frequentValuesList0: List[Dict[str, int]]  # Frequencies of values for opponent0
    frequentValuesList1: List[Dict[str, int]]  # Frequencies of values for opponent0

    opp0bag = List[str]  # Bag of values for opponent0
    opp1bag = List[str]  # Bag of values for opponent1

    @property
    def name(self) -> str:
        return "RubickAgent"

    def initiate(self, opponent_name: Optional[str]):
        # Default values
        self.parties = []
        self.history = []
        self.histOpp0 = []
        self.histOpp1 = []
        self.isHistoryAnalyzed = False
        self.numberOfReceivedOffer = 0
        self.profileOrder = []
        self.opponentNames = ["", ""]
        self.acceptanceLimits = [0., 0.]
        self.lastpartyname = ""
        self.bestAcceptedBids = []
        self.threshold = self.preference.reservation_value
        self.maxReceivedBidutil = self.threshold

        self.frequentValuesList0 = []
        self.frequentValuesList1 = []

        self.opp0bag = []
        self.opp1bag = []

        # Initiate opponent model
        self.initializeOpponentModelling()

    def initializeOpponentModelling(self):
        """
            This agent applies a frequentist opponent model approach for each opponent agents. This method initiates
            the opponent models.
        :return: Nothing
        """
        issueSize = len(self.preference.issues)

        for i in range(issueSize):
            self.frequentValuesList0.append({})
            self.frequentValuesList1.append({})

            issuecnt = 0

            for issue in self.preference.issues:
                if issuecnt == i:
                    for value in issue.values:
                        self.frequentValuesList0[i][value] = 0
                        self.frequentValuesList1[i][value] = 0

                issuecnt += 1

    def receive_offer(self, bid: nenv.Bid, t: float):
        # TODO: This method will be changed when Multilateral or Repeated Negotiation features are implemented.

        self.lastReceivedBid = bid.copy()

        # Update maximum received utility
        if self.maxReceivedBidutil < self.preference.get_utility(self.lastReceivedBid):
            self.maxReceivedBidutil = self.preference.get_utility(self.lastReceivedBid) * 0.95

        self.numberOfReceivedOffer += 1

        # Framework does not support Multilateral and Repeated Negotiations yet.
        self.lastpartyname = "Opponent"

        # Update opponent model
        self.BidResolver(self.lastReceivedBid, "Opponent")

        if "Opponent" not in self.parties:
            self.sortPartyProfiles("Opponent")

        if len(self.parties) >= 3 and len(self.history) != 0 and not self.isHistoryAnalyzed:
            self.analyzeHistory()

    def act(self, t: float) -> nenv.Action:
        decisiveUtil = self.checkAcceptance(t)

        if decisiveUtil == -1:
            return self.accept_action

        bid = self.generateBid(decisiveUtil, t)

        return nenv.Offer(bid)

    def takeTheChange(self, maxReceived: float) -> float:
        """
            This method randomly selects a power value based on the maximum received utility.
        :param maxReceived: Maximum received utility
        :return: Power value
        """
        pow = 1
        chance = random.random()

        if chance > 0.95 + 0.05 * maxReceived:
            pow = 2
        elif chance > 0.93 + 0.07 * maxReceived:
            pow = 3
        else:
            pow = 10

        return pow

    def checkAcceptance(self, t: float) -> int:
        """
            This method applies acceptance strategy which is a Time-Based approach.
        :param t: Current negotiation time
        :return: -1: Acceptable, Otherwise: Unacceptable
        """
        pow = self.takeTheChange(self.maxReceivedBidutil)

        # Get a random target utility
        targetUtil = 1 - (math.pow(t, pow) * abs(random.gauss(0, 1) / 3.))

        if self.numberOfReceivedOffer < 2:  # Do not accept in first two rounds
            return 1
        elif len(self.history) != 0:
            upperLimit = self.maxReceivedBidutil

            for du in self.acceptanceLimits:
                if upperLimit < du:
                    upperLimit = du

            upperLimit *= 0.9
            pow = self.takeTheChange(upperLimit)

            targetUtil = 1 - (math.pow(t, pow) * abs(random.gauss(0, 1) / 3.))
            targetUtil = upperLimit + (1 - upperLimit) * targetUtil
        else:
            if self.maxReceivedBidutil < 0.8:
                self.maxReceivedBidutil = 0.8

            targetUtil = self.maxReceivedBidutil + (1 - self.maxReceivedBidutil) * targetUtil

        if self.preference.get_utility(self.lastReceivedBid) > targetUtil or t > 0.999:  # Acceptance conditions
            return -1

        return targetUtil

    def generateBid(self, targetUtil: float, t: float) -> nenv.Bid:
        """
            This method makes an offer based on the given target utility.
        :param targetUtil: Target utility
        :param t: Current negotiation time
        :return: Bid
        """
        if t > 0.995 and len(self.bestAcceptedBids) != 0:  # Near to deadline
            s = len(self.bestAcceptedBids)

            if s > 3:
                s = 3

            ind = random.randint(0, s - 1)
            return self.bestAcceptedBids[ind]

        bid = None

        if self.checkSearchable():  # Search a bid which is beneficial for both agents
            bid = self.searchCandidateBids(targetUtil)

        if bid is None:  # If we cannot find any bid
            return self.preference.get_bid_at(targetUtil)

        return bid

    def checkSearchable(self) -> bool:
        """
            For search a bid, the bags of the opponent must not be empty.
        :return: Check for conditions
        """

        # For bilateral: only check opp0bag
        # For multilateral: check both bags
        if len(self.opp0bag) > 0:
            if len(self.opp1bag) > 0:
                # Multilateral: both bags must have same length
                return len(self.opp0bag) == len(self.opp1bag)
            else:
                # Bilateral: only opp0bag needed
                return True

        return False

    def searchCandidateBids(self, targetUtil: float) -> Optional[nenv.Bid]:
        """
            This method tries to find a bid which not only is beneficial for both opponents but also has a higher
            utility than the given target utility.
        :param targetUtil: Target utility
        :return: Selected bid
        """
        bu = 0.
        valu = None

        intersection = []
        candidateBids = []

        for bid in self.preference.bids:
            bu = bid.utility

            if bu >= targetUtil:  # The selected bid must have a higher utility value than the target utility.
                score = 0

                # Count intersection values
                for isn, issue in enumerate(bid.content.keys()):
                    valu = bid[issue]

                    if valu == self.opp0bag[isn]:
                        score += 1
                    if len(self.opp1bag) > 0 and valu == self.opp1bag[isn]:
                        score += 1

                intersection.append(score)
                candidateBids.append(bid.copy())
            else:
                break

        maxIdx = -1
        maxVal = -1
        for i in range(len(intersection)):
            if maxVal < intersection[i]:
                maxVal = intersection[i]
                maxIdx = i

        if len(candidateBids) > 0:
            return candidateBids[maxIdx]

        return None  # Cannot find

    def BidResolver(self, bid: nenv.Bid, partyname: str):
        """
            This method updates the opponent model.
        :param bid: Received bid
        :param partyname: Name of the opponent
        :return: Nothing
        """
        valu = None

        if partyname == self.opponentNames[0]:
            for issue in bid.content.keys():
                valu = bid[issue]
                isn = self.preference.issues.index(issue)
                self.frequentValuesList0[isn][valu] += 1
        elif partyname == self.opponentNames[1]:
            for issue in bid.content.keys():
                valu = bid[issue]
                isn = self.preference.issues.index(issue)
                self.frequentValuesList1[isn][valu] += 1

        if self.numberOfReceivedOffer > 2:
            self.extractOpponentPreferences()

    def extractOpponentPreferences(self):
        """
            This method extracts a common preferences from the estimated value weights of the opponents.
        :return: Nothing
        """
        opp0priors = []
        opp1priors = []

        self.opp0bag = []
        self.opp1bag = []

        medianEvalValues0 = []
        medianEvalValues1 = []

        for i in range(len(self.frequentValuesList0)):
            medianEvalValues0.append(self.median(self.frequentValuesList0[i]))
            medianEvalValues1.append(self.median(self.frequentValuesList1[i]))

        for i in range(len(self.frequentValuesList0)):
            for val in self.frequentValuesList0[i].keys():
                if self.frequentValuesList0[i][val] >= medianEvalValues0[i]:
                    opp0priors.append(val)

            if len(opp0priors) > 0:
                self.opp0bag.append(random.choice(opp0priors))

            for val in self.frequentValuesList1[i].keys():
                if self.frequentValuesList1[i][val] >= medianEvalValues1[i]:
                    opp1priors.append(val)

            if len(opp1priors) > 0:
                self.opp1bag.append(random.choice(opp1priors))

    def median(self, fvl: dict) -> float:
        """
            This method finds the median value
        :param fvl: Frequencies of values in an issue.
        :return: Median value
        """
        valFreqs = [v for v in fvl.values()]

        valFreqs.sort()

        middle = len(valFreqs) // 2

        if len(valFreqs) % 2 == 1:
            return valFreqs[middle]
        else:
            return (valFreqs[middle - 1] + valFreqs[middle]) / 2.

    def analyzeHistory(self):
        """
            This method analyzes the previous negotiation history. This method will be change when Multilateral or
            Repeated Negotiation features are implemented in the framework.
        :return: Nothing
        """

        # TODO: This method will be changed when Multilateral or Repeated Negotiation features are implemented.

        self.isHistoryAnalyzed = True

        for h in range(len(self.history)):
            utilsOp1 = []
            utilsOp2 = []

    def sortPartyProfiles(self, partyID: str):
        """
            This method sorts opponents. This method will be change when Multilateral or Repeated Negotiation features
            are implemented in the framework.
        :param partyID: Name of the opponent
        :return: Nothing
        """

        # TODO: This method will be changed when Multilateral or Repeated Negotiation features are implemented.

        self.profileOrder.append(0)
        self.parties.append(partyID)
        self.opponentNames[0] = partyID
