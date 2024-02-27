from typing import Dict

import nenv


class BidSelector:
    """
        This class helps to select a bid based on a given utility
    """
    pref: nenv.Preference               # Preferences
    BidList: Dict[float, nenv.Bid]      # Utility-Bid mapping

    def __init__(self, pref: nenv.Preference):
        """
            Constructor. It also generates the BidList dictionary.
        :param pref: Preferences of the agent
        """
        self.pref = pref
        self.BidList = {}

        InitialBid = {issue: issue.values[0] for issue in self.pref.issues}

        b = nenv.Bid(InitialBid)
        self.BidList[self.pref.get_utility(b)] = b

        for issue in self.pref.issues:
            TempBids = {}

            # We add a small negative value to use floorEntry and lowerEntry methods
            d = -0.00000001

            for TBid in self.BidList.values():
                for value in issue.values:
                    NewBidV = TBid.copy()
                    NewBidV[issue] = value

                    webid = NewBidV.copy()

                    TempBids[self.pref.get_utility(webid) + d] = NewBidV

                    d -= 0.00000001

            self.BidList = TempBids
