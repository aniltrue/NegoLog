from typing import Optional
import nenv
from agents.AgentKN.etc.negotiatingInfo import negotiatingInfo
from agents.AgentKN.etc.bidSearch import bidSearch
from agents.AgentKN.etc.negotiationStrategy import strategy
from nenv import Bid


class AgentKN(nenv.AbstractAgent):
    """
        **AgentKN by Keita Nakamura**:
            AgentKN searches 10 bids that maximize self utility value while randomly shifting the initial bid. In
            bidding strategy, it decides the bid according to the self utility value and frequency that opponents have
            offered. First, it searches 10 bids that maximize self utility. Next, it sorts 10 bids by self utility and
            issue values, frequency, and offers. In searching the local-optimal bids, it uses Simulated Annealing, and
            searches 10 bids that maximize self utility value while randomly shifting the initial bid. It sorts by the
            following scores: ::math:: `(utility)+ 0.1^(log10frequency+1)*frequency*utility` is the individual utility,
            frequency is the sum of the number of values of issues opponents offered in the previous rounds. In
            acceptance strategy, it accepts when the utility value of the opponents bid exceeded the threshold at that
            time. The threshold is decided as the following equation: :math: `threshold(t) = 1 − (1 − emax(t))∗tα` (
            emax(t) is the estimated the opponent’s maximum utility, and α(¿1) is the parameter of conseccing to the
            emax(t). It estimates max utility value that opponents may offer:

            .. math::
                emax(t)=µ(t)+(1 − \mu(t))d(t)

                d(t)= (\sqrt{3}\sigma(t)) / (\sqrt{\mu(t)(1 − \mu(t)})

            (µ(t): Average of utility values that the opponent have offered, d(t):Estimated width of the bid range of
            the opponent, which uses the concession strategy, σ(t): Standard deviation of utility value that the
            opponent has offered) [Aydogan2021]_

        ANAC 2017 Nash product category finalist.

        .. [Aydogan2021] Reyhan Aydoğan, Katsuhide Fujita, Tim Baarslag, Catholijn M. Jonker, and Takayuki Ito. ANAC 2017: Repeated multilateral negotiation league. In Advances in Auto- mated Negotiations, pages 101–115, Singapore, 2021. Springer Singapore.
    """
    negotiatingInfo: negotiatingInfo
    bidSearch: bidSearch
    negotiatingStrategy: strategy
    mLastReceivedBid: Optional[nenv.Bid]
    mOfferedBid: Optional[nenv.Bid]
    nrChosenActions: int
    history: list

    @property
    def name(self) -> str:
        return "AgentKN"

    def initiate(self, opponent_name: Optional[str]):
        self.mOfferedBid = None
        self.mLastReceivedBid = None
        self.nrChosenActions = 0

        self.negotiatingInfo = negotiatingInfo(self.preference)
        self.bidSearch = bidSearch(self.preference, self.negotiatingInfo)
        self.negotiatingStrategy = strategy(self.preference, self.negotiatingInfo)
        self.history = []
        self.negotiatingInfo.updateOpponentsNum(1)

    def act(self, t: float) -> nenv.Action:
        self.negotiatingInfo.updateTimeScale(t)

        if self.can_accept() and self.negotiatingStrategy.selectAccept(self.mOfferedBid, t):
            return self.accept_action
        else:
            return self.OfferAction(t)

    def OfferAction(self, t: float) -> nenv.Action:
        offerBid = self.bidSearch.getBid(self.preference.get_random_bid(), self.negotiatingStrategy.getThreshold(t))

        self.negotiatingInfo.updateMyBidHistory(offerBid)

        return nenv.Offer(offerBid)

    def receive_offer(self, bid: Bid, t: float):
        sender = "OpponentAgent"

        if sender not in self.negotiatingInfo.opponents:
            self.negotiatingInfo.initOpponent(sender)

        self.mOfferedBid = bid.copy()
        self.negotiatingInfo.updateInfo(sender, bid)
        self.negotiatingInfo.updateOfferedValueNum(sender, bid, t)
