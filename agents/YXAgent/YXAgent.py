import math
from typing import List, Dict, Optional
import nenv


class YXAgent(nenv.AbstractAgent):
    """
        ANAC 2016 individual utility category runner-up. [Aydogan2021]_

        .. [Aydogan2021] Reyhan Aydoğan, Katsuhide Fujita, Tim Baarslag, Catholijn M. Jonker, and Takayuki Ito. ANAC 2017: Repeated multilateral negotiation league. In Advances in Auto- mated Negotiations, pages 101–115, Singapore, 2021. Springer Singapore.
    """
    myAction: nenv.Action
    myLastBid: nenv.Bid
    lastOpponentBid: nenv.Bid

    myUtility: float
    oppUtility: float
    rv: float
    discountFactor: float
    rounds: int
    updatedValueIntegerWeight: bool
    issueContainIntegerType: bool
    searchedDiscountWithRV: bool

    opponents: list
    allBids: List[nenv.Bid]
    oppBidHistory: Dict[str, List[nenv.Bid]]
    oppIssueWeight: Dict[str, Dict[nenv.Issue, float]]
    oppIssueIntegerValue: Dict[str, Dict[nenv.Issue, List[int]]]
    oppValueFrequency: Dict[str, Dict[nenv.Issue, Dict[str, float]]]
    oppSumDiff: Dict[str, float]
    hardestOpp: str

    @property
    def name(self) -> str:
        return "YXAgent"

    def initiate(self, opponent_name: Optional[str]):
        self.rv = self.preference.reservation_value
        self.discountFactor = 1.0

        self.allBids = []
        self.opponents = []
        self.oppBidHistory = {}
        self.oppIssueWeight = {}
        self.oppIssueIntegerValue = {}
        self.oppValueFrequency = {}
        self.oppSumDiff = {}

        self.rounds = 0
        self.updatedValueIntegerWeight = False
        self.issueContainIntegerType = False
        self.searchedDiscountWithRV = False
        self.oppUtility = 0.

    def receive_offer(self, bid: nenv.Bid, t: float):
        sender = "OpponentAgent"

        if sender not in self.opponents:
            self.opponents.append(sender)
            self.initOpp(sender)

        self.lastOpponentBid = bid.copy()
        self.oppUtility = bid.utility
        self.allBids.append(self.lastOpponentBid)

        self.updateOpp(sender, t)

    def act(self, t: float) -> nenv.Action:
        self.rounds += 1

        testBid = None
        v: str
        calUtil = 0.
        calThreshold: float
        tempThreshold: float
        minimalThreshold = 0.7
        deductThreshold = 0.2
        calculatedThreshold = 1 - (len(self.opponents) * deductThreshold)

        tempThreshold = max(max(minimalThreshold, calculatedThreshold), self.rv)

        if not self.can_accept():
            myLastBid = self.preference.get_random_bid()
            myUtility = myLastBid.utility

            while myUtility < minimalThreshold:
                myLastBid = self.preference.get_random_bid()
                myUtility = myLastBid.utility

            return nenv.Offer(myLastBid)

        testBid = self.preference.get_random_bid()
        myUtility = testBid.utility

        while myUtility < tempThreshold:
            testBid = self.preference.get_random_bid()
            myUtility = testBid.utility

        if self.rounds > 10 and t <= 0.9:
            for issue in self.issues:
                v = self.lastOpponentBid[issue]

                calUtil += self.oppIssueWeight[self.hardestOpp][issue] * self.oppValueFrequency[self.hardestOpp][issue][
                    v]

            calThreshold = calUtil - ((len(self.opponents) * deductThreshold) * 3 / 4)
            calThreshold = max(tempThreshold, calThreshold)
            myAction = self.accept_action if self.oppUtility > calThreshold else nenv.Offer(testBid)

            return myAction
        else:
            myAction = self.accept_action if self.oppUtility > tempThreshold else nenv.Offer(testBid)

            return myAction

    def updateOpp(self, sender, t):
        self.updateModelOppIssueWeight(sender, t)
        self.updateModelOppValueWeight(sender, t)
        self.oppBidHistory[sender].append(self.lastOpponentBid)
        self.retrieveToughestOpp()

    def updateModelOppIssueWeight(self, sender, t):
        if len(self.oppBidHistory[sender]) != 0 and self.rounds >= 10:
            previousRoundBid = self.oppBidHistory[sender][-1]

            issueWeightFormula = (math.pow((1 - t), 10)) / (len(self.issues) * 100)
            issueSum = 0

            for issue in self.issues:
                prevIssueValue = previousRoundBid[issue]
                currentIssueValue = self.lastOpponentBid[issue]

                if prevIssueValue == currentIssueValue:
                    self.oppIssueWeight[sender][issue] += issueWeightFormula

                issueSum += self.oppIssueWeight[sender][issue]

            for issue in self.issues:
                self.oppIssueWeight[sender][issue] /= issueSum

    def updateModelOppValueWeight(self, sender, t):
        maxValueBase = 0.
        valueWeightFormula = math.pow(0.2, t) / 30000

        for issue in self.issues:
            value = self.lastOpponentBid[issue]
            self.oppValueFrequency[sender][issue][value] += valueWeightFormula

        for issue in self.issues:
            maxValueBase = max(self.oppValueFrequency[sender][issue].values())

            for value in issue.values:
                self.oppValueFrequency[sender][issue][value] /= maxValueBase

    def retrieveToughestOpp(self):
        self.hardestOpp = self.opponents[0] if len(self.opponents) > 0 else "OpponentAgent"

    def initOpp(self, sender):
        self.oppIssueIntegerValue[sender] = {}
        self.initModelOppIssueWeight(sender)
        self.initModelOppValueFrequency(sender)
        self.oppBidHistory[sender] = []

    def initModelOppIssueWeight(self, sender):
        avgW = 1. / len(self.issues)

        self.oppIssueWeight[sender] = {}

        for issue in self.issues:
            self.oppIssueWeight[sender][issue] = avgW

    def initModelOppValueFrequency(self, sender):
        self.oppValueFrequency[sender] = {}
        for issue in self.issues:
            self.oppValueFrequency[sender][issue] = {}

            for value in issue.values:
                self.oppValueFrequency[sender][issue][value] = 1.

    @property
    def issues(self) -> List[nenv.Issue]:
        return self.preference.issues
