from typing import List, Tuple
import numpy as np
import nenv


class OpponentBid:
    """
        OpponentBid class holds a bid with its offered time
    """
    bid: nenv.Bid           # Bid content
    time: float             # Negotiation time when offered
    pref: nenv.Preference   # Preferences of the Agent

    def __init__(self, bid: nenv.Bid, time: float, pref: nenv.Preference):
        """
            Constructor
        :param bid: Bid content
        :param time: Negotiation time
        :param pref: Preferences of the agent
        """
        self.bid = bid
        # Set utility
        self.bid.utility = pref.get_utility(bid)
        self.time = time
        self.pref = pref

    def __lt__(self, other):
        """
            We can compare the OpponentBid objects based on the utility:
                obj1 < obj2
        :param other: Other OpponentBid object
        :return: self < other
        """
        return self.bid < other.bid

    def __le__(self, other):
        """
            We can compare the OpponentBid objects based on the utility:
                obj1 <= obj2
        :param other: Other OpponentBid object
        :return: self <= other
        """
        return self.bid <= other.bid

    def __gt__(self, other):
        """
            We can compare the OpponentBid objects based on the utility:
                obj1 > obj2
        :param other: Other OpponentBid object
        :return: self > other
        """
        return self.bid > other.bid

    def __ge__(self, other):
        """
            We can compare the OpponentBid objects based on the utility:
                obj1 >= obj2
        :param other: Other OpponentBid object
        :return: self >= other
        """
        return self.bid >= other.bid


class OpponentHistory:
    """
        OpponentHistory class holds the list of OpponentBid objects. It also generates the corresponding
        numpy arrays for the training.
    """
    history: List[OpponentBid]  # List of OpponentBid

    def __init__(self):
        """
            Constructor
        """
        self.history = []   # Initially empty

    def get_data(self, first_bid: nenv.Bid) -> Tuple[np.ndarray, np.ndarray]:
        """
            This method generates the corresponding X and Y numpy arrays for the training.
        :param first_bid: First bid of the opponent for adjusting.
        :return: X and Y numpy arrays
        """
        # Declare X and Y list
        x = []
        y = []
        # Inputs will be adjusted for a better result
        x_adjust = []
        intercept = first_bid.utility
        gradient = 0.9 - intercept  #

        for opponent_bid in self.history:
            # X: Negotiation Time, Y: Utility
            x.append(opponent_bid.time)
            y.append(opponent_bid.bid.utility)
            # x_adjust = first_utility + gradient * t
            x_adjust.append(intercept + (gradient * opponent_bid.time))

        # Convert into numpy array
        x = np.reshape(np.array(x, dtype=np.float32), (-1, 1))
        y = np.reshape(np.array(y, dtype=np.float32) - x_adjust, (-1, 1))

        return x, y

    def get_maximum_bid(self) -> OpponentBid:
        """
            Return the bid with the maximum utility in that history
        :return: OpponentBid which has the maximum utility
        """
        return max(self.history)
