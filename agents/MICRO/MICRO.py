import random
from typing import Optional, Set

import nenv
from nenv import Action, Bid


class MICROAgent(nenv.AbstractAgent):
    """
        **MiCRO agent by Dave de Jonge**:
            MICRO Agent concedes only when the opponent concedes. [deJonge2022]_

        ANAC 2022 individual utility category runner-up.

        .. [deJonge2022] Dave de Jonge. An analysis of the linear bilateral ANAC domains using the MiCRO benchmark strategy. In Luc De Raedt, editor, Proceedings of the Thirty-First International Joint Conference on Artificial Intelligence, IJCAI 2022, Vienna, Austria, 23-29 July 2022, pages 223–229. ijcai.org, 2022.
    """
    my_last_bid: nenv.Bid           #: My last offered bid
    index: int                      #: Number of unique proposals made by me
    increase: int                   #: Increase amount
    received_bids: Set[nenv.Bid]    #: Unique received bids

    @property
    def name(self) -> str:
        return "MiCRO"

    def initiate(self, opponent_name: Optional[str]):
        # Set default values
        self.my_last_bid = self.preference.bids[0]
        self.index = 1
        self.increase = 1
        self.received_bids = set()

    def receive_offer(self, bid: Bid, t: float):
        # Store unique received bids
        self.received_bids.add(bid)

    def act(self, t: float) -> Action:
        # If MiCRO agent starts, offer the bid with the highest utility
        if len(self.last_received_bids) == 0:
            return nenv.Offer(self.my_last_bid)

        # If the opponent makes enough number of unique bid, then concede
        ready_to_concede = self.index <= len(self.received_bids)

        # Next bid to offer
        self.my_last_bid = self.preference.bids[self.index - 1]

        # AC_Next strategy to decide accepting or not
        if self.my_last_bid.utility <= self.last_received_bids[-1] >= self.preference.reservation_value:
            return self.accept_action

        # If the opponent conceded
        if ready_to_concede and self.my_last_bid.utility > self.preference.reservation_value:
            # Increase the number of unique proposals made by me
            self.index += self.increase

            # Make concession
            self.my_last_bid = self.preference.bids[self.index - 1]

            ''' If the opponent has not yet proposed the next bid, then check if there exists some alternative bid 
                with the same utility and that has been proposed by the opponent. 
                If we can find such a bid then that one should be proposed first.
            '''
            self.my_last_bid = self.find_alternative_bid()

            return nenv.Offer(self.my_last_bid)
        else:
            # Select a random bid
            self.my_last_bid = self.preference.bids[0] if self.index == 1 else random.choice(self.preference.bids[:self.index])

            return nenv.Offer(self.my_last_bid)

    def find_alternative_bid(self) -> Bid:
        # If the next bid has been already proposed by the opponent, then offer it
        if self.my_last_bid in self.received_bids:
            return self.my_last_bid

        for i in range(self.index, len(self.preference.bids)):
            alternative_bid = self.preference.bids[i]

            if alternative_bid.utility < self.my_last_bid.utility:
                # All alternative offers have been already tested
                return self.my_last_bid

            if alternative_bid not in self.received_bids:
                # Candidate bid has been not proposed yet.
                continue

            return alternative_bid

        return self.my_last_bid
