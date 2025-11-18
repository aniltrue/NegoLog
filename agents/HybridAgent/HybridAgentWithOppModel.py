import math
from typing import List, Optional
import nenv
from nenv import Bid, Action, Offer


class HybridAgentWithOppModel(nenv.AbstractAgent):
    """
        This agent is extension version of Hybrid Agent by considering opponent model. [Yesevi2022]_

        .. [Yesevi2022] Yesevi, G., Keskin, M.O., Doğru, A., Aydoğan, R. (2023). Time Series Predictive Models for Opponent Behavior Modeling in Bilateral Negotiations. In: Aydoğan, R., Criado, N., Lang, J., Sanchez-Anguix, V., Serramia, M. (eds) PRIMA 2022: Principles and Practice of Multi-Agent Systems. PRIMA 2022. Lecture Notes in Computer Science(), vol 13753. Springer, Cham. <https://doi.org/10.1007/978-3-031-21203-1_23>
        .. [Keskin2021] Mehmet Onur Keskin, Umut Çakan, and Reyhan Aydoğan. 2021. Solver Agent: Towards Emotional and Opponent-Aware Agent for Human-Robot Negotiation. In Proceedings of the 20th International Conference on Autonomous Agents and MultiAgent Systems (AAMAS '21). International Foundation for Autonomous Agents and Multiagent Systems, Richland, SC, 1557–1559.
    """
    p0: float  #: Initial utility
    p1: float  #: Concession ratio
    p2: float  #: Final utility
    p3: float  #: Empathy Score

    window_lower_bound: float  #: Bid Search window lower bound
    window_upper_bound: float  #: Bid Search window upper bound
    repetition_limit: int      #: Number of previous bids to avoid repetition

    opponent_model: nenv.OpponentModel.AbstractOpponentModel  # Opponent Model

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
        return "Hybrid with OppModel"

    def initiate(self, opponent_name: Optional[str]):
        # Set default values
        self.p0 = 1.0
        self.p1 = 0.75
        self.p2 = 0.55
        self.p3 = 0.5

        # Set p2, and bid search window bound based on domain size
        domain_size = len(self.preference.bids)

        if domain_size < 450:
            self.window_upper_bound = 0.1
            self.window_lower_bound = 0.1
        elif domain_size < 1500:
            self.window_upper_bound = 0.09
            self.window_lower_bound = 0.09
        elif domain_size < 4500:
            self.window_upper_bound = 0.08
            self.window_lower_bound = 0.08
        elif domain_size < 18000:
            self.window_lower_bound = 0.07
            self.window_upper_bound = 0.07
        elif domain_size < 33000:
            self.window_upper_bound = 0.06
            self.window_lower_bound = 0.06
        else:
            self.window_upper_bound = 0.05
            self.window_lower_bound = 0.05

        # Initiate opponent model
        self.opponent_model = nenv.OpponentModel.WindowedFrequencyOpponentModel(self.preference)

        self.repetition_limit = 10

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
        # Update opponent model

        self.opponent_model.update(bid, t)

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

        # Find the bid
        bid = self.bid_search(target_utility)

        # AC_Next strategy to decide accepting or not
        if self.can_accept() and (target_utility <= self.last_received_bids[-1].utility or bid.utility <= self.last_received_bids[-1].utility):
            return self.accept_action

        self.my_last_bids.append(bid)

        return Offer(bid)

    def bid_search(self, target_utility: float) -> nenv.Bid:
        """
            This method applies Windowed-Bid search approach. Firstly, it collects the all bids around the given target
            utility. Then, it returns a bid with the highest estimated Nash product.
        :param target_utility: Target utility
        :return: The bid with the highest estimated Nash product around target utility.
        """
        target_bid = self.preference.get_bid_at(target_utility)

        estimated_preference = self.opponent_model.preference

        bids = self.get_bids_at_circle(target_bid, estimated_preference)

        # If no bid is in the window, return the closest bid to target utility
        if len(bids) == 0:
            return target_bid

        selected_bid: Optional[nenv.Bid] = None

        if len(self.my_last_bids) <= self.repetition_limit:
            last_bids = self.my_last_bids
        else:
            last_bids = self.my_last_bids[-self.repetition_limit:]

        # Select the highest estimated Nash product bid by avoiding repetition
        for bid in bids:
            if bid in last_bids:
                continue

            nash = bid.utility * estimated_preference.get_utility(bid)

            if selected_bid is None or nash > selected_bid.utility * estimated_preference.get_utility(selected_bid):
                selected_bid = bid

        if selected_bid is not None:
            return selected_bid

        # Select the highest estimated Nash product bid without avoiding repetition
        for bid in bids:
            nash = bid.utility * estimated_preference.get_utility(bid)

            if selected_bid is None or nash > selected_bid.utility * estimated_preference.get_utility(selected_bid):
                selected_bid = bid

        return selected_bid

    def get_bids_at_circle(self, target_bid: nenv.Bid, estimated_preference: nenv.OpponentModel.EstimatedPreference) -> List[nenv.Bid]:
        my_utility = target_bid.utility
        opp_utility = estimated_preference.get_utility(target_bid)

        bids = self.preference.get_bids_at(my_utility, self.window_lower_bound, self.window_upper_bound)

        window_bids = []

        for bid in bids:
            distance = math.sqrt(math.pow(my_utility - bid.utility, 2.) + math.pow(opp_utility - estimated_preference.get_utility(bid), 2.))

            if distance <= max(self.window_upper_bound, self.window_lower_bound):
                window_bids.append(bid)

        return window_bids
