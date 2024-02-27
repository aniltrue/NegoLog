from typing import List
import nenv
from agents.Caduceus2015.SaneUtilitySpace import SaneUtilitySpace


class BidRecord:
    roundNumber: int
    bid: nenv.Bid

    def __init__(self, roundNumber: int, bid: nenv.Bid):
        self.roundNumber = roundNumber
        self.bid = bid


class Opponent:
    identifier: str
    history: List[nenv.Bid]
    saneUtilitySpace: SaneUtilitySpace

    def __init__(self, identifier: str, pref: nenv.Preference):
        self.identifier = identifier
        self.history = []
        self.saneUtilitySpace = SaneUtilitySpace(pref)
        self.saneUtilitySpace.init_zero()

        for issue in self.saneUtilitySpace.issues:
            self.saneUtilitySpace[issue] = 1e-10

            for value in issue.values:
                self.saneUtilitySpace[issue, value] = 1e-10

    def addToHistory(self, receivedBid: nenv.Bid):
        self.history.append(receivedBid)
