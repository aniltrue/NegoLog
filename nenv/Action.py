from nenv.Bid import Bid
from abc import ABC
from typing import Optional


class Action(ABC):
    """
        An agent returns an Offer, Accept, or EndNegotiation action. Only offers
        and acceptances carry a bid; ending a session yields reservation utility.
    """
    bid: Optional[Bid]  #: Corresponding bid, absent when ending negotiation

    def __init__(self, bid: Optional[Bid]):
        self.bid = bid


class Offer(Action):
    """
        If agent makes an offer (or counter-offer), it should return Offer Action.
    """
    def __str__(self):
        return "Offer: " + str(self.bid)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.__str__().__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()


class Accept(Offer):
    """
        If agent accepts the opponent's bid, it should return Accept Action.
    """
    def __str__(self):
        return "Accept: " + str(self.bid)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.__str__().__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()


class EndNegotiation(Action):
    """End the session without agreement, retaining a human-readable reason."""

    def __init__(self, reason: str = "agent ended negotiation"):
        if not isinstance(reason, str):
            raise ValueError("End reason must be a string")
        super().__init__(None)
        self.reason = reason or "agent ended negotiation"

    def __str__(self):
        return "End: " + self.reason

    def __repr__(self):
        return str(self)
