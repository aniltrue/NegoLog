from typing import Optional
import nenv
from agents.Atlas3.etc.negotiatingInfo import negotiatingInfo
from agents.Atlas3.etc.bidSearch import bidSearch
from agents.Atlas3.etc.strategy import strategy
from nenv import Bid


class Atlas3Agent(nenv.AbstractAgent):
    """
    **Atlas3 agent by Akiyuki Mori**:
        Atlas3 agent uses appropriate searching method based on relative utility for
        linear utility spaces. Moreover, it applies replacement method based on frequency of opponent’s bidding history.
        It decides concession value according to the concession function presented by us in Mori and Ito (A compromising
        strategy based on expected utility of evolutionary stable strategy in bilateral closed bargaining problem, 2015,
        [Mori2015]_). In Mori and Ito (A compromising strategy based on expected utility of evolutionary stable strategy
        in bilateral closed bargaining problem, 2015, [Mori2015]_), an estimated expected utility is derived to estimate
        an appropriate lower limits of concession function. However, Mori and Ito (A compromising strategy based on
        expected utility of evolutionary stable strategy in bilateral closed bargaining problem, 2015, [Mori2015]_)
        proposes a concession function for bilateral multi-issue closed bargaining games. Therefore, the concession
        function is extended for multi-lateral multi-issue closed bargaining games. [Mori2017]_

    ANAC 2015 individual utility & nash product category winner.

    .. [Mori2017] Mori, A., Ito, T. (2017). Atlas3: A Negotiating Agent Based on Expecting Lower Limit of Concession Function. In: Fujita, K., et al. Modern Approaches to Agent-based Complex Automated Negotiation. Studies in Computational Intelligence, vol 674. Springer, Cham. <https://doi.org/10.1007/978-3-319-51563-2_11>
    .. [Mori2015] Mori, A., & Ito, T. (2015). A compromising strategy based on expected utility of evolutionary stable strategy in bilateral closed bargaining problem. Proceedings of agent-based complex automated negotiations, 58-65.

    """
    negotiatingInfo: negotiatingInfo
    bidSearch: bidSearch
    strategy: strategy
    rv: float
    offeredBid: Optional[nenv.Bid]
    supporter_num: int
    CList_index: int

    @property
    def name(self) -> str:
        return "Atlas3"

    def initiate(self, opponent_name: Optional[str]):
        self.offeredBid = None
        self.supporter_num = 0
        self.CList_index = 0

        self.negotiatingInfo = negotiatingInfo(self.preference)
        self.bidSearch = bidSearch(self.preference, self.negotiatingInfo)
        self.strategy = strategy(self.preference, self.negotiatingInfo)
        self.rv = self.preference.reservation_value

    def act(self, t: float) -> nenv.Action:
        self.negotiatingInfo.updateTimeScale(t)

        CList = self.negotiatingInfo.pb_list

        if t > 1. - self.negotiatingInfo.time_scale * (len(CList) + 1):
            return self.chooseFinalAction(self.offeredBid, CList, t)

        if self.can_accept() and self.strategy.selectAccept(self.offeredBid, t):
            return self.accept_action

        return self.OfferAction(t)

    def chooseFinalAction(self, offeredBid: nenv.Bid, CList: list, t: float) -> nenv.Action:
        offered_bid_util = 0.

        if offeredBid is not None:
            offered_bid_util = self.preference.get_utility(offeredBid)

        if self.CList_index >= len(CList):
            if offered_bid_util >= self.rv:
                return self.accept_action

            return self.OfferAction(t)

        CBid = CList[self.CList_index]
        CBid_util = self.preference.get_utility(CBid)

        if CBid_util > offered_bid_util and CBid_util > self.rv:
            self.CList_index += 1
            self.negotiatingInfo.updateMyBidHistory(CBid)

            return nenv.Offer(CBid)
        elif offered_bid_util > self.rv:
            return self.accept_action

        return self.OfferAction(t)

    def OfferAction(self, t: float) -> nenv.Action:
        offerBid = self.bidSearch.getBid(self.preference.get_random_bid(), self.strategy.getThreshold(t))

        self.negotiatingInfo.updateMyBidHistory(offerBid)

        return nenv.Offer(offerBid)

    def receive_offer(self, bid: Bid, t: float):
        sender = "OpponentAgent"

        if sender not in self.negotiatingInfo.opponents:
            self.negotiatingInfo.initOpponent(sender)

        self.supporter_num = 1
        self.offeredBid = bid.copy()
        self.negotiatingInfo.updateInfo(sender, bid)
