from typing import List, Optional
import nenv
from nenv import Bid, Action, Offer


class HybridAgent(nenv.AbstractAgent):
    """
        Hybrid Agent combines Time-Based and Behavior-Based strategies. [Keskin2021]_


        .. [Keskin2021] Mehmet Onur Keskin, Umut Çakan, and Reyhan Aydoğan. 2021. Solver Agent: Towards Emotional and Opponent-Aware Agent for Human-Robot Negotiation. In Proceedings of the 20th International Conference on Autonomous Agents and MultiAgent Systems (AAMAS '21). International Foundation for Autonomous Agents and Multiagent Systems, Richland, SC, 1557–1559.
    """
    p0: float   #: Initial utility
    p1: float   #: Concession ratio
    p2: float   #: Final utility
    p3: float   #: Empathy Score

    # Window for Behavior-Based strategy
    W = {
        1: [1],
        2: [0.25, 0.75],
        3: [0.11, 0.22, 0.66],
        4: [0.05, 0.15, 0.3, 0.5],
    }
    my_last_bids: List[Bid]  # My last offered bids

    @property
    def name(self) -> str:
        return "Hybrid"

    def initiate(self, opponent_name: Optional[str]):
        # Set default values
        self.p0 = 1.0
        self.p1 = 0.75
        self.p2 = 0.55
        self.p3 = 0.5

        self.my_last_bids = []

        self.p2 = max(self.p2, self.preference.reservation_value)

    def time_based(self, t: float) -> float:
        """
            Target utility calculation of Time-Based strategy
        :param t: Negotiation time
        :return: Target utility
        """
        return (1 - t) * (1 - t) * self.p0 + 2 * (1 - t) * t * self.p1 + t * t * self.p2

    def behaviour_based(self, t: float) -> float:
        """
            Target utility calculation of Behavior-Based strategy
        :param t: Negotiation time
        :return: Target utility
        """

        # Utility differences of consecutive offers of opponent
        diff = [self.last_received_bids[i + 1].utility - self.last_received_bids[i].utility
                for i in range(len(self.last_received_bids) - 1)]

        # Fixed size window
        if len(diff) > len(self.W):
            diff = diff[-len(self.W):]

        # delta = diff * window
        delta = sum([u * w for u, w in zip(diff, self.W[len(diff)])])

        # Calculate target utility by updating the last offered bid
        target_utility = self.my_last_bids[-1].utility - (self.p3 + self.p3 * t) * delta

        return target_utility

    def receive_offer(self, bid: Bid, t: float):
        # Do nothing when an offer received.

        pass

    def act(self, t: float) -> Action:
        # Target utility of Time-Based strategy
        target_utility = self.time_based(t)

        # If first 2 round, apply only Time-Based strategy
        if len(self.last_received_bids) > 2:
            # Target utility of Behavior-Based strategy
            behaviour_based_utility = self.behaviour_based(t)

            # Combining Time-Based and Behavior-Based strategy
            target_utility = (1. - t * t) * behaviour_based_utility + t * t * target_utility

        # Target utility cannot be lower than the reservation value.
        if target_utility < self.preference.reservation_value:
            target_utility = self.preference.reservation_value

        # AC_Next strategy to decide accepting or not
        if self.can_accept() and target_utility <= self.last_received_bids[-1].utility:
            return self.accept_action

        # Find the closest bid to target utility
        bid = self.preference.get_bid_at(target_utility)

        self.my_last_bids.append(bid)

        return Offer(bid)
