from typing import Optional
import nenv
from nenv import Bid, Action, Offer


class BoulwareAgent(nenv.AbstractAgent):
    """
        Time-Based Concession Agent based on [Faratin1998]_

        **Target Utility Calculation** based on [Vahidov2017]_:

        .. math::
            {TU} = (1 - t)^2 P_0 + (1 - t) t P_1 + t^2 P_2

            P_1 \geq (P_0 + P_1) / 2

        .. [Faratin1998] Peyman Faratin, Carles Sierra, and Nick R. Jennings. 1998. Negotiation decision functions for autonomous agents. Robotics and Autonomous Systems 24, 3 (1998), 159–182.
        .. [Vahidov2017] Rustam M. Vahidov, Gregory E. Kersten, and Bo Yu. 2017. Human-Agent Ne-gotiations: The Impact Agents’ Concession Schedule and Task Complexity onAgreements. In 50th Hawaii International Conference on System Sciences, HICSS2017, Tung Bui (Ed.). ScholarSpace / AIS Electronic Library (AISeL), Hawaii, 1–9
    """
    p0: float   #: Initial utility
    p1: float   #: Concession ratio
    p2: float   #: Final utility

    @property
    def name(self) -> str:
        return "Boulware"

    def initiate(self, opponent_name: Optional[str]):
        # Set default values
        self.p0 = 1.0
        self.p1 = 0.85
        self.p2 = 0.4

        # Update for reservation value
        if self.preference.reservation_value > self.p2:
            ratio = (self.p0 + self.p2) / 2

            self.p2 = self.preference.reservation_value

            updated_ratio = (self.p0 + self.p2) / 2

            self.p1 = updated_ratio / ratio * self.p1

    def receive_offer(self, bid: Bid, t: float):
        # Do nothing when an offer received.

        pass

    def act(self, t: float) -> Action:
        # Calculate target utility to offer
        target_utility = (1 - t) * (1 - t) * self.p0 + 2 * (1 - t) * t * self.p1 + t * t * self.p2

        # Target utility cannot be lower than the reservation value.
        if target_utility < self.preference.reservation_value:
            target_utility = self.preference.reservation_value

        # AC_Next strategy to decide accepting or not
        if self.can_accept() and target_utility <= self.last_received_bids[-1]:
            return self.accept_action

        # Find the closest bid to target utility
        bid = self.preference.get_bid_at(target_utility)

        return Offer(bid)
