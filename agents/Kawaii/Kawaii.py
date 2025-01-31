from typing import Optional
import nenv
from agents.Kawaii.NegotiatingInfo import NegotiatingInfo
from agents.Kawaii.BidSearch import BidSearch
from agents.Kawaii.Strategy import Strategy


class Kawaii(nenv.AbstractAgent):
    """
        ANAC 2015 individual utility category runner-up. [Baarslag2015]_

        .. [Baarslag2015] Baarslag, T., Aydoğan, R., Hindriks, K. V., Fujita, K., Ito, T., & Jonker, C. M. (2015). The Automated Negotiating Agents Competition, 2010–2015. AI Magazine, 36(4), 115-118. <https://doi.org/10.1609/aimag.v36i4.2609>
    """
    negotiatingInfo: NegotiatingInfo
    bidSearch: BidSearch
    strategy: Strategy
    offeredBid: Optional[nenv.Bid]

    def initiate(self, opponent_name: Optional[str]):
        self.negotiatingInfo = NegotiatingInfo(self.preference)

        self.bidSearch = BidSearch(self.preference, self.negotiatingInfo)
        self.strategy = Strategy(self.preference, self.negotiatingInfo)

        self.offeredBid = None

    @property
    def name(self) -> str:
        return "Kawaii"

    def act(self, t: float) -> nenv.Action:
        if self.can_accept() and self.strategy.selectAccept(self.offeredBid, t):
            return self.accept_action

        return self.OfferAction(t)

    def OfferAction(self, t: float):
        offeredBid = self.bidSearch.getBid(self.preference.get_random_bid(), self.strategy.getThreshold(t))

        self.negotiatingInfo.MyBidHistory.append(offeredBid)

        return nenv.Offer(offeredBid)

    def receive_offer(self, bid: nenv.Bid, t: float):
        sender = "OpponentAgent"

        if sender not in self.negotiatingInfo.opponents:
            self.negotiatingInfo.initOpponent(sender)

        self.offeredBid = bid.copy()

        self.negotiatingInfo.opponentsBool[sender] = False

