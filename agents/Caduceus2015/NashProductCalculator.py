from typing import List, Optional
from agents.Caduceus2015.SaneUtilitySpace import SaneUtilitySpace
import nenv


class NashProductCalculator:
    utilitySpaces: List[SaneUtilitySpace]

    nashProduct: float
    nashBid: Optional[nenv.Bid]

    def __init__(self, utilitySpaces: list):
        self.utilitySpaces = utilitySpaces
        self.nashProduct = 0.
        self.nashBid = None

        for utilitySpace in utilitySpaces:
            utilitySpace.normalize()

    def calculate(self, pref: nenv.Preference):
        tempProduct = 1.

        count = 0

        for i, currentBid in enumerate(pref.bids):
            for utilitySpace in self.utilitySpaces:
                u = utilitySpace.get_utility(currentBid)
                tempProduct *= u

            if tempProduct == 1.:
                count += 1

            if tempProduct > self.nashProduct:
                self.nashProduct = tempProduct
                self.nashBid = currentBid
