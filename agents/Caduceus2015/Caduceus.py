from typing import Dict, Optional
import nenv
from agents.Caduceus2015.UtilFunctions import *
from agents.Caduceus2015.CounterOfferGenerator import CounterOfferGenerator
from agents.Caduceus2015.NashProductCalculator import NashProductCalculator
from agents.Caduceus2015.Opponent import Opponent
from agents.Caduceus2015.SaneUtilitySpace import SaneUtilitySpace


class Caduceus2015(nenv.AbstractAgent):
    """
        **Caduceus agent by Taha Güneş**:
            This agent is developed as a sub-agent for Caduceus agent. [Gunes2017]_

        .. [Gunes2017] Güneş, T.D., Arditi, E., Aydoğan, R. (2017). Collective Voice of Experts in Multilateral Negotiation. In: An, B., Bazzan, A., Leite, J., Villata, S., van der Torre, L. (eds) PRIMA 2017: Principles and Practice of Multi-Agent Systems. PRIMA 2017. Lecture Notes in Computer Science(), vol 10621. Springer, Cham. <https://doi.org/10.1007/978-3-319-69131-2_27>
    """
    discountFactor: float
    numberOfOpponents: int
    selfReservationValue: float
    percentageOfOfferringBestBid: float
    mySaneUtilitySpace: Optional[SaneUtilitySpace]
    opponentProfiles: Dict[str, Opponent]
    previousBid: nenv.Bid
    takeConcessionStep: bool

    opponentMap: Dict[str, Opponent]

    def initiate(self, opponent_name: Optional[str]):
        self.discountFactor = 1.
        self.selfReservationValue = max(self.preference.reservation_value, 0.75)
        self.percentageOfOfferringBestBid = 0.83 * self.discountFactor
        self.numberOfOpponents = 1
        self.opponentProfiles = {}
        self.opponentMap = {}
        self.mySaneUtilitySpace = None
        self.takeConcessionStep = True

    @property
    def name(self) -> str:
        return "Caduceus2015"

    def act(self, t: float) -> nenv.Action:
        if self.isBestOfferTime(t):
            bestBid = self.getBestBid()

            if bestBid is not None:
                return nenv.Offer(bestBid)
        else:
            bid = self.getMyBestOfferForEveryone(t)

            if bid is not None:
                if self.preference.get_utility(bid) < self.selfReservationValue:
                    bid = self.preference.get_random_bid()

                if self.can_accept() and self.preference.get_utility(self.previousBid) > self.preference.get_utility(bid) + 0.2:
                    return self.accept_action

            return nenv.Offer(bid)
        return nenv.Offer(self.getBestBid())

    def getMyBestOfferForEveryone(self, time: float) -> nenv.Bid:
        utilitySpaces = [self.getMySaneUtilitySpace()]

        for utilitySpace in self.opponentProfiles.values():
            utilitySpaces.append(utilitySpace.saneUtilitySpace)

        npc = NashProductCalculator(utilitySpaces)
        npc.calculate(self.preference)

        if npc.nashBid is None:
            bestBid = self.getBestBid()
            offerGenerator = CounterOfferGenerator(bestBid, self)

            return offerGenerator.generateBid(time)

        cog = CounterOfferGenerator(npc.nashBid, self)

        return cog.generateBid(time)

    def isBestOfferTime(self, t: float) -> bool:
        return t < self.percentageOfOfferringBestBid

    def receive_offer(self, bid: nenv.Bid, t: float):
        sender = "OpponentAgent"

        opponentProfile: Opponent
        uglyBid = bid.copy()

        self.getMySaneUtilitySpace()

        if sender not in self.opponentProfiles:
            opponentProfile = Opponent(sender, self.preference)
        else:
            opponentProfile = self.opponentProfiles[sender]

        self.previousBid = uglyBid

        previousBid: Optional[nenv.Bid] = None

        if len(opponentProfile.history) > 0:
            previousBid = opponentProfile.history[-1]

            for issue, value in bid:
                opponentProfile.saneUtilitySpace[issue, value] += self.getRoundValue(t)

                if previousBid is not None and previousBid[issue] == value:
                    opponentProfile.saneUtilitySpace[issue] += self.getRoundValue(t)

        opponentProfile.history.append(uglyBid)

        self.opponentProfiles[sender] = opponentProfile

    def getBestBid(self):
        return self.preference.bids[0].copy()

    def getMySaneUtilitySpace(self):
        if self.mySaneUtilitySpace is None:
            self.mySaneUtilitySpace = SaneUtilitySpace(self.preference)
            self.mySaneUtilitySpace.init_copy(self.preference)

        return self.mySaneUtilitySpace

    def getRoundValue(self, t: float):
        roundValue = (2 * math.pow(t, 2)) - (101 * t) + 100

        return float("%.3f" % roundValue)

