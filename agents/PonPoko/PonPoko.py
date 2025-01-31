import math
import random
from typing import Optional
import nenv
from nenv import Action, Bid


class PonPokoAgent(nenv.AbstractAgent):
    """
        **PonPokoAgent by Takaki Matsune**:

            PonPokoAgent tries to propose new offers to compromise the opponents offers as the time passes.However, it
            has several different bidding strategies and selects the one of them randomly because it is hard for the
            opponents to predict PonPoko agent strategy through the previous sessions. In addition,it tries to obtain
            the high individual utilities just before the deadline. In the bidding strategy, it makes the list including
            all bids available in the domain at the beginning of the negotiation. It has 2 parameters to decide the
            highest/lowest utility of PonPoko agent offers, and 5 patterns decide these parameters (time means the
            negotiation time elapsed [0,1]). [Aydogan2021]_

        ANAC 2017 individual utility category winner.

        .. [Aydogan2021] Reyhan Aydoğan, Katsuhide Fujita, Tim Baarslag, Catholijn M. Jonker, and Takayuki Ito. ANAC 2017: Repeated multilateral negotiation league. In Advances in Auto- mated Negotiations, pages 101–115, Singapore, 2021. Springer Singapore.
    """
    lastReceivedBid: nenv.Bid
    threshold_low: float
    threshold_high: float
    PATTERN_SIZE = 5
    pattern: int

    @property
    def name(self) -> str:
        return "PonPoko"

    def initiate(self, opponent_name: Optional[str]):
        self.threshold_low = .99
        self.threshold_high = 1.0

        self.pattern = random.choice(list(range(self.PATTERN_SIZE + 1)))

    def receive_offer(self, bid: Bid, t: float):
        self.lastReceivedBid = bid.copy()

    def act(self, t: float) -> Action:
        if self.pattern == 0:
            self.threshold_high = 1 - .1 * t
            self.threshold_low = 1 - .1 * t - .1 * abs(math.sin(t * 40))
        elif self.pattern == 1:
            self.threshold_high = 1.
            self.threshold_low = 1 - .22 * t
        elif self.pattern == 2:
            self.threshold_high = 1. - .1 * t
            self.threshold_low = 1 - .1 * t - .15 * abs(math.sin(t * 20))
        elif self.pattern == 3:
            self.threshold_high = 1. - 0.05 * t
            self.threshold_low = 1. - 0.1 * t

            if t > .99:
                self.threshold_low = 1 - 0.3 * t
        elif self.pattern == 4:
            self.threshold_high = 1. - 0.15 * t * abs(math.sin(t * 20))
            self.threshold_low = 1. - 0.21 * t * abs(math.sin(t * 20))
        else:
            self.threshold_high = 1. - 0.1 * t
            self.threshold_low = 1. - 0.2 * abs(math.sin(t * 40))

        if self.can_accept():
            if self.preference.get_utility(self.lastReceivedBid) > self.threshold_low:
                return self.accept_action

        bid = None
        while bid is None:
            bid = self.selectBidfromList()

            if bid is None:
                self.threshold_low -= 0.0001

        return nenv.Offer(bid)

    def selectBidfromList(self):
        bids = []

        for bid in self.preference.bids:
            if self.threshold_low <= bid.utility <= self.threshold_high:
                bids.append(bid)

            if bid.utility < self.threshold_low:
                break

        if len(bids) == 0:
            return None

        return random.choice(bids)
