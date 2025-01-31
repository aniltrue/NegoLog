import math
from typing import List, Union, Optional
import numpy as np
from nenv.Preference import Preference
from nenv.Bid import Bid


class BidPoint:
    """
        BidPoint class holds the Bid object with the utilit values of each agent.
    """
    __bid: Optional[Bid]     #: Corresponding Bid object
    __utility_a: float       #: Utility value of AgentA
    __utility_b: float       #: Utility value of AgentB

    def __init__(self, bid: Optional[Bid], utility_a: float, utility_b: float):
        """
            Constructor

            :param bid: Corresponding Bid object
            :param utility_a: Utility value of AgentA
            :param utility_b: Utility value of AgentB
        """
        self.__bid = bid
        self.__utility_a = utility_a
        self.__utility_b = utility_b

    @property
    def bid(self) -> Optional[int]:
        """

            :return: Copy of Bid object without utility value
        """
        if self.__bid is None:
            return None

        return self.__bid.copy()

    @property
    def utility_a(self) -> float:
        """

            :return: Utility value of AgentA
        """
        return self.__utility_a

    @property
    def utility_b(self) -> float:
        """

            :return: Utility value of AgentB
        """
        return self.__utility_b

    @property
    def product_score(self) -> float:
        """

            :return: Product Score of this BidPoint
        """
        return self.__utility_a * self.__utility_b

    @property
    def social_welfare(self) -> float:
        """

            :return: Social welfate of this BidPoint
        """
        return self.__utility_a + self.__utility_b

    def distance(self, bid_point) -> float:
        """
            This method calculates the Euclidean distance between the BidPoints

            :Example:
                Example usage of distance calculation

                >>> bid_point1 = BidPoint(None, 1.0, 0.5)
                >>> bid_point2 = BidPoint(None, 0.5, 1.0)
                >>> distance = bid_point1.distance(bid_point2)
                >>> print(round(distance, 2)) # 0.71

            :param bid_point: Other BidPoint
            :return: Euclidean distance between bid points in the corresponding bid space
        """
        return math.sqrt((self.__utility_a - bid_point.utility_a) ** 2 + (self.__utility_b - bid_point.utility_b) ** 2)

    def dominate(self, bid_point) -> bool:
        """
            This method determine whether the bid point dominates the other one

            :param bid_point: Other BidPoint
            :return: Whether bid point dominates the other one
        """
        return ((self.utility_a > bid_point.utility_a or self.utility_b > bid_point.utility_b) and
                (self.utility_a >= bid_point.utility_a and self.utility_b >= bid_point.utility_b))

    def __sub__(self, bid_point) -> float:
        """
            *"-"* operator implementation that returns the distance between the bid points.

            :Example:
                Example usage of distance calculation

                >>> bid_point1 = BidPoint(None, 1.0, 0.5)
                >>> bid_point2 = BidPoint(None, 0.5, 1.0)
                >>> distance = bid_point1 - bid_point2
                >>> print(round(distance, 2)) # 0.71

            :param bid_point: Other BidPoint
            :return: Euclidean distance between bid points in the corresponding bid space
        """
        return self.distance(bid_point)

    def __eq__(self, other):
        """
            "==" operator implementation that compares the offer contents.

            :param other: Bid, BidPoint or offer content
            :return: Whether the offer contents are same, or not
        """
        if isinstance(other, BidPoint):
            return self.__bid.__eq__(other.__bid)
        else:
            return self.__bid.__eq__(other)

    def __str__(self):
        """

            :return: String version of the offer content
        """
        return self.__bid.__str__()

    def __hash__(self):
        """

            :return: The hash value of the offer content
        """
        return self.__bid.__hash__()

    def __repr__(self):
        """

            :return: The representation of the offer content
        """
        return self.__bid.__repr__()

    def __gt__(self, other):
        """
            ">" operator implementation to compare two BidPoints in terms of the nash product

            :param other: Another BidPoint that will be compared
            :return: bid_point > other
        """
        return self.product_score > other.product_score

    def __ge__(self, other):
        """
            ">=" operator implementation to compare two BidPoints in terms of the nash product

            :param other: Another BidPoint that will be compared
            :return: bid_point >= other
        """
        return self.product_score >= other.product_score

    def __lt__(self, other):
        """
            "<" operator implementation to compare two BidPoints in terms of the nash product

            :param other: Another BidPoint that will be compared
            :return: bid_point < other
        """
        return self.product_score < other.product_score

    def __le__(self, other):
        """
            "<=" operator implementation to compare two BidPoints in terms of the nash product

            :param other: Another BidPoint that will be compared
            :return: bid_point <= other
        """
        return self.product_score <= other.product_score


class BidSpace:
    """
        Bid space of preferences of the agents.
    """
    prefA: Preference                   #: Preferences of agentA
    prefB: Preference                   #: Preferences of agentB
    __bids: List[BidPoint]              #: The bid points of the bid space
    __nash_point: Optional[BidPoint]    #: Nash Point of the bid space
    __kalai_point: Optional[BidPoint]   #: Kalai Point of the bid space
    __pareto: Optional[List[BidPoint]]  #: Pareto-frontier of the bid space

    def __init__(self, prefA: Preference, prefB: Preference):
        """
            Constructor

            :param prefA: Preferences of agentA
            :param prefB: Preferences of agentB
        """
        self.prefA = prefA
        self.prefB = prefB
        self.__bids = []
        self.__nash_point = None
        self.__kalai_point = None
        self.__pareto = None

    @property
    def bid_points(self):
        """
            The bid points of the bid space. It is initiated when the first call.

            :return: The bid points of the bid space
        """
        if len(self.__bids) > 0:
            return self.__bids

        for bid in self.prefA.bids:
            self.__bids.append(
                BidPoint(bid.copy_without_utility(), self.prefA.get_utility(bid), self.prefB.get_utility(bid)))

            if self.__nash_point is None or self.__kalai_point is None:
                self.__nash_point = BidPoint(bid.copy_without_utility(), self.prefA.get_utility(bid),
                                             self.prefB.get_utility(bid))
                self.__kalai_point = BidPoint(bid.copy_without_utility(), self.prefA.get_utility(bid),
                                              self.prefB.get_utility(bid))

            if self.__nash_point.product_score < self.__bids[-1].product_score:
                self.__nash_point = BidPoint(bid.copy_without_utility(), self.prefA.get_utility(bid),
                                             self.prefB.get_utility(bid))
            if self.__kalai_point.social_welfare < self.__bids[-1].social_welfare:
                self.__kalai_point = BidPoint(bid.copy_without_utility(), self.prefA.get_utility(bid),
                                              self.prefB.get_utility(bid))

        return self.__bids

    @property
    def pareto(self) -> List[BidPoint]:
        """
            The list of BidPoint on the Pareto-Frontier

            :return: List of BidPoint on the Pareto-Frontier
        """
        if self.__pareto is not None:
            return self.__pareto

        bids = self.bid_points

        pareto_indices = [True for _ in range(len(bids))]

        for i in range(len(bids)):
            point_i = np.array([bids[i].utility_a, bids[i].utility_b])

            if not pareto_indices[i]:
                continue

            for j in range(i + 1, len(bids)):
                if not pareto_indices[i]:
                    break

                if not pareto_indices[j]:
                    continue

                point_j = np.array([bids[j].utility_a, bids[j].utility_b])

                if all(point_j >= point_i) and any(point_j > point_i):
                    pareto_indices[i] = False

                    break

                if all(point_i >= point_j) and any(point_i > point_j):
                    pareto_indices[j] = False

        pareto_bids = []

        for index in range(len(bids)):
            if pareto_indices[index]:
                pareto_bids.append(bids[index])

        self.__pareto = pareto_bids

        return pareto_bids

    @property
    def nash_point(self) -> BidPoint:
        """
            The Bid Point which has the highest Nash Product

            :return: Nash point of the bid space as BidPoint
        """
        if self.__nash_point is None:
            _ = self.bid_points

        return self.__nash_point

    @property
    def kalai_point(self) -> BidPoint:
        """
            The Bid Point which has the highest Social Welfare

            :return: Kalai point of the bid space as BidPoint
        """
        if self.__kalai_point is None:
            _ = self.bid_points

        return self.__kalai_point

    @property
    def nash_score(self) -> float:
        """
            The highest Product Score

            :return: Product Score of the Nash point
        """
        return self.nash_point.product_score

    @property
    def kalai_score(self) -> float:
        """
            The highest Social Welfare

            :return: Social Welfare of the Kalai point
        """
        return self.kalai_point.social_welfare

    def calculate_opposition(self) -> float:
        """
            This method calculates the **opposition** score of this bid space.

        :return: Opposition score
        """
        return self.kalai_distance(BidPoint(None, 1., 1.))

    def calculate_balance_score(self) -> float:
        """
            This method calculates the **balance score** of this bid space.

        :return: Balance Score
        """

        bids_a = self.prefA.bids
        bids_b = self.prefB.bids

        total_diff = 0.

        for i in range(len(bids_a)):
            total_diff += bids_a[i].utility - bids_b[i].utility

        return total_diff / len(bids_a)

    def calculate_normalized_balance_score(self) -> float:
        """
            This method calculates the **normalized balance score** of this bid space.

        :return: Normalized Balance Score
        """

        bids_a = self.prefA.bids
        bids_b = self.prefB.bids

        nash_point = self.nash_point

        nash_zero = nash_point - BidPoint(None, 0., 0.)

        total_diff = 0.

        for i in range(len(bids_a)):
            nash_distance = nash_point - BidPoint(None, bids_a[i].utility, bids_b[i].utility)

            total_diff += (bids_a[i].utility - bids_b[i].utility) * nash_distance / (nash_zero + 1e-12)

        return total_diff

    def get_bid_point(self, bid: Bid) -> BidPoint:
        """
            This method converts given bid into *BidPoint* object

            :Example:
                Example of converting a Bid object to BidPoint object

                >>> bid_point = bid_space.get_bid_point(bid)

            :param bid: Corresponding bid that will be converted into BidPoint object
            :return:  that is converted from the given bid.
        """
        return BidPoint(bid, self.prefA.get_utility(bid), self.prefB.get_utility(bid))

    def nash_distance(self, target: Union[Bid, BidPoint]) -> float:
        """
            Euclidean distance between the target and Nash point

            :param target: The target as Bid or BidSpace
            :return: Euclidean distance
        """
        if isinstance(target, BidPoint):
            return target - self.nash_point
        if isinstance(target, Bid):
            return self.get_bid_point(target) - self.nash_point

    def kalai_distance(self, target: Union[Bid, BidPoint]) -> float:
        """
            Euclidean distance between the target and Kalai point

            :param target: The target as Bid or BidSpace
            :return: Euclidean distance
        """
        if isinstance(target, BidPoint):
            return target - self.kalai_point
        if isinstance(target, Bid):
            return self.get_bid_point(target) - self.kalai_point

    def __len__(self):
        """
            The number of Bids

            :Example:
                You can get the number of bids:

                >>> size = len(bid_space)

            :return: Number of bids in the bid space
        """
        return len(self.__bids)

    def __iter__(self):
        """
            This method helps you to iterate over all BidPoint in that BidSpace object. Example:

            :Example:
                Example for loop

                >>> for bid_point in bid_space:
                >>>     ...

            :return: List Iterator
        """
        return self.__bids.__iter__()
