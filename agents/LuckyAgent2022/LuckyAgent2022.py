import math
import random
from typing import Optional
import numba
import numpy as np
from agents.LuckyAgent2022.OpponentModel import OpponentModel
import nenv
from nenv import Action, Bid


class LuckyAgent2022(nenv.AbstractAgent):
    """
        **LuckAgent2022 by Arash Ebrahimnezhad**:
            LuckyAgent2022 has BOA components and its learning methods over negotiation sessions. To improve its utility
            over sessions, it proposes SLM, a LSN Stop-Learning mechanism, to prevent overfitting by adapting it to a
            multi-armed bandit problem. It finds the best value for variables of a time-dependent bidding strategy for
            the opponent. [Ebrahimnezhad2022]_

        ANAC 2022 individual utility category runner-up.

        .. [Ebrahimnezhad2022]  A. Ebrahimnezhad and F. Nassiri-Mofakham, LuckyAgent2022: A Stop-Learning Multi-Armed Bandit Automated Negotiating Agent. 2022 13th International Conference on Information and Knowledge Technology (IKT), Karaj, Iran, Islamic Republic of, 2022, pp. 1-6, doi: 10.1109/IKT57960.2022.10039035.
    """
    alpha: float
    betta: float
    NUMBER_OF_GOALS: int = 5
    agreement_utility: float
    who_accepted: Optional[str]
    is_called: bool

    max: float
    min: float
    e: float
    increasing_e: float
    decreasing_e: float
    epsilon: float
    good_agreement_u: float
    condition_d: float

    opponent_model: OpponentModel

    @property
    def name(self) -> str:
        return "LuckAgent2022"

    def initiate(self, opponent_name: Optional[str]):
        self.alpha = 1.0
        self.betta = 0.0
        self.agreement_utility = 0.0
        self.who_accepted = None
        self.is_called = False

        self.max = 1.0
        self.min = 0.6
        self.e = 0.05
        self.increasing_e = 0.025
        self.decreasing_e = 0.025
        self.epsilon = 1.0
        self.good_agreement_u = 0.95
        self.condition_d = 0

        self.opponent_model = OpponentModel(self.preference)

    def receive_offer(self, bid: Bid, t: float):
        self.opponent_model.update(bid, t)

    def act(self, t: float) -> Action:
        self.cal_thresholds(t)

        if not self.can_accept():
            return nenv.Offer(self.preference.bids[0])

        next_bid = self.find_bid()
        # check if the last received offer is good enough
        if self.accept_condition(t, self.last_received_bids[-1], next_bid):
            # if so, accept the offer
            action = self.accept_action
        else:
            # if not, find a bid to propose as counter offer
            action = nenv.Offer(next_bid)
            # self.my_bids.append(next_bid)

        # send the action
        return action

    def accept_condition(self, t: float, received_bid: Bid, next_bid) -> bool:
        if received_bid is None or not self.can_accept():
            return False

        progress = t

        # set reservation value
        reservation = self.preference.reservation_value

        received_bid_utility = self.preference.get_utility(received_bid)
        condition1 = received_bid_utility >= self.threshold_acceptance and received_bid_utility >= reservation
        condition2 = progress > 0.97 and received_bid_utility > self.min and received_bid_utility >= reservation
        condition3 = self.alpha * float(received_bid_utility) + self.betta >= self.preference.get_utility(next_bid) and received_bid_utility >= reservation

        return condition1 or condition2 or condition3

    def cal_thresholds(self, t: float):
        progress = t
        self.threshold_high = self.p(self.min + 0.1, self.max, self.e, progress)
        self.threshold_acceptance = self.p(self.min + 0.1, self.max, self.e, progress) - (0.1 * (progress + 0.0000001))
        self.threshold_low = self.p(self.min + 0.1, self.max, self.e, progress) - (0.1 * (
                    progress + 0.0000001)) * abs(math.sin(progress * 60))

    def find_bid(self) -> Bid:
        """
        @return next possible bid with current target utility, or null if no such
                bid.
        """
        interval = self.threshold_high - self.threshold_low
        s = interval / self.NUMBER_OF_GOALS

        utility_goals = []
        for i in range(self.NUMBER_OF_GOALS):
            utility_goals.append(self.threshold_low + s * i)
        utility_goals.append(self.threshold_high)

        options = self.preference.get_bids_at(random.choice(utility_goals), lower_bound=0.01, upper_bound=0.01)

        opponent_utilities = []
        for option in options:
            if self.opponent_model != None:
                opp_utility = float(
                    self.opponent_model.preference.get_utility(option))
                if opp_utility > 0:
                    opponent_utilities.append(opp_utility)
                else:
                    opponent_utilities.append(0.00001)
            else:
                opponent_utilities.append(0.00001)

        if len(options) == 0:
            # if we can't find good bid, get max util bid....
            options = self.preference.get_bids_at(self.preference.bids[0].utility, lower_bound=0.01, upper_bound=0.01)

            return options[random.randint(0, len(options) - 1)]
        # pick a random one.

        next_bid = random.choices(list(options), weights=opponent_utilities)[0]

        for bid_detaile in self.last_received_bids:
            if self.preference.get_utility(bid_detaile) >= self.preference.get_utility(next_bid):
                next_bid = bid_detaile

        return random.choices(options, weights=opponent_utilities)[0]

    @numba.jit(nopython=True)
    def ff(self, ll, n):
        x_list = []
        for x in ll[::-1]:
            if x[1] == n:
                x_list.append(x[0])
            else:
                break
        if len(x_list) > 0:
            m = np.mean(x_list)
        else:
            m = 0.8
        return m

    def f(self, t, k, e):
        return k + (1 - k) * (t ** (1 / e))

    def p(self, min1, max1, e, t):
        return min1 + (1 - self.f(t, 0, e)) * (max1 - min1)
