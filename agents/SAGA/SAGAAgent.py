import math
import random
from typing import Optional
import numpy as np
import nenv
from agents.SAGA.GeneticAlgorithm import GeneticAlgorithm


class SAGAAgent(nenv.AbstractAgent):
    """
        **SAGA Agent by Yuta Hosokawa**:
            SAGA Agent applies Genetic Algorithm approach to estimate the self preferences. In Genetic Algorithm, the
            fitness function is based on Spearman metric. For the bidding and acceptance strategies, it has Time-Based
            approaches. [Aydogan2020]_

        ANAC 2019 individual utility category finalist.

        .. [Aydogan2020] Aydoğan, R. et al. (2020). Challenges and Main Results of the Automated Negotiating Agents Competition (ANAC) 2019. In: Bassiliades, N., Chalkiadakis, G., de Jonge, D. (eds) Multi-Agent Systems and Agreement Technologies. EUMAS AT 2020 2020. Lecture Notes in Computer Science(), vol 12520. Springer, Cham. <https://doi.org/10.1007/978-3-030-66412-1_23>
    """
    rnd: random.Random                              #: Random object
    lastOffer: Optional[nenv.Bid]                   #: Last received bid
    isFirst: bool                                   #: Whether the received bid is the first, or not
    firstUtil: float                                #: Utility value of the first received bid
    pref: nenv.Preference                           #: Estimated preferences of the SAGA Agent

    def initiate(self, opponent_name: Optional[str]):
        # Default values
        self.isFirst = True
        self.firstUtil = 0.95
        self.rnd = random.Random()
        self.lastOffer = None

        # Apply Genetic Algorithm to estimate preferences
        # ga = GeneticAlgorithm(self.preference)

        # self.pref = ga.estimate_preferences()

        self.pref = self.preference

    def act(self, t: float) -> nenv.Action:
        # Calculate target utility
        target = self.getTarget(t)

        if self.lastOffer is not None:
            # Utility of last received bid
            util = self.pref.get_utility(self.lastOffer)

            # Check acceptance strategy
            if self.can_accept() and self.isAcceptable(t, target, util):
                return self.accept_action

        # Make an offer
        return nenv.Offer(self.generateRandomBidAbove(target))

    def isAcceptable(self, time: float, target: float, util: float) -> bool:
        """
            This method decide to accept by applying a Time-Based approach.

            The acceptance strategy has three steps depending on the negotiation time.
        :param time: Current negotiation time
        :param target: Target utility
        :param util: The utility value of the last received bid
        :return: Acceptance or not
        """

        # Check for reservation value
        if util < self.preference.reservation_value:
            return False

        # Parameters
        timeA = 0.6     # Time to start giving Accept rate below Target
        timeB = 0.997   # Time to start giving Accept rate to all bids

        if time <= timeA:       # First Step
            a = (util - target) / (1. - target + 1e-10)
            b = math.pow(3, (0.5 - time) * 2)

            acceptProb = np.power(a, b)

            return self.rnd.random() < acceptProb
        elif time >= timeB:     # Third Step
            acceptProb = math.pow(util, 2)

            return self.rnd.random() < acceptProb

        # Second Step: when timeA < time < timeB
        APatT = 0.15 * math.pow((time - timeA) / (1 - timeA + 1e-10), 2)
        acceptBase = target - (1 - target) * (time - timeA) / (1 - timeA + 1e-10)

        if util > target:
            acceptProb = APatT + (1 - APatT) * math.pow((util - target) / (1 - target + 1e-10), math.pow(3, (0.5 - time) * 2))

            return self.rnd.random() < acceptProb
        elif util > acceptBase:
            acceptProb = APatT * math.pow((util - acceptBase) / (target - acceptBase + 1e-10), 2)

            return self.rnd.random() < acceptProb

        return False

    def getTarget(self, time: float) -> float:
        """
            This method calculates the target utility by applying a Time-Based approach.
        :param time: Current negotiation time
        :return: Target utility
        """

        # Parameters
        A = 0.6
        B = 5

        # Minimum target utility bound based on the utility value of the first received bid.
        targetMin = self.firstUtil + A * (1 - self.firstUtil)

        # Minimum target utility bound cannot be less than reservation value
        if targetMin < self.preference.reservation_value:
            targetMin = self.preference.reservation_value

        # Calculate target utility
        return targetMin + (1 - targetMin) * (1 - math.pow(time, B))

    def generateRandomBidAbove(self, target: float):
        """
            This method generates a random bid which has a utility value higher than the given target utiltiy.
        :param target: Target utility
        :return: Randomly selected bid
        """
        return self.pref.get_random_bid(lower_bound=target)

    def receive_offer(self, bid: nenv.Bid, t: float):
        # Update last received bid
        self.lastOffer = bid

        # If the bid is the first received bid
        if self.isFirst:
            self.firstUtil = self.pref.get_utility(self.lastOffer)
            self.isFirst = False

    @property
    def name(self) -> str:
        return "SAGA"
