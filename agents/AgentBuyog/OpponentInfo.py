from typing import List

import nenv
from agents.NiceTitForTat.helpers.BidHistory import BidHistory


class OpponentInfo:
    agentID: str
    agentBidHistory: BidHistory
    bestBids: BidHistory
    pref: nenv.OpponentModel.EstimatedPreference
    leniency: float
    domainCompetitiveness: float
    agentDifficulty: float
    bestBid: nenv.Bid
    bidPointWeights: List[int]

    def __init__(self, agentID: str, pref: nenv.Preference):
        self.agentID = agentID
        self.agentBidHistory = BidHistory()
        self.bestBids = BidHistory()
        self.bestBid = None
        self.domainCompetitiveness = None
        self.leniency = None
        self.pref = nenv.OpponentModel.EstimatedPreference(pref)
        self.bidPointWeights = []
        self.agentDifficulty = None

        self.initializeOpponentUtilitySpace()

    def initializeOpponentUtilitySpace(self):
        numberOfIssues = len(self.pref.issues)

        commonWeight = 1. / numberOfIssues

        for issue in self.pref.issues:
            self.pref[issue] = commonWeight

            for value in issue.values:
                self.pref[issue, value] = 1.

    def containsBid(self, bid: nenv.Bid):
        for bidDetail in self.agentBidHistory.history:
            if bidDetail.bid == bid:
                return True

        return False
