from typing import List
from agents.Caduceus2015.UtilFunctions import *
import nenv


class CounterOfferGenerator:
    nashBid: nenv.Bid
    concessionStep: float
    NUMBER_OF_ROUNDS_FOR_CONCESSION: int = 10
    vectorSize: int
    allPossibleBids: List[nenv.Bid]
    bidSpace: List[List[float]]

    def __init__(self, nashBid: nenv.Bid, party, concessionStep: float = 0.2):
        self.party = party
        self.nashBid = nashBid
        self.concessionStep = concessionStep
        self.vectorSize = len(nashBid.content)
        self.allPossibleBids = []

        self.calculateAllPossibleBids()

        self.bidSpace = []
        self.vectorizeAll()

    def getUnitVector(self) -> list:
        maxBid = self.party.preference.bids[0].copy()
        maxBidPoint = self.vectorizeBid(maxBid)

        nashPoint = self.vectorizeBid(self.nashBid)

        unitVector = calculateUnitVector(maxBidPoint, nashPoint)

        return unitVector

    def vectorizeAll(self):
        for i, bid in enumerate(self.allPossibleBids):
            point = self.vectorizeBid(bid)
            self.bidSpace.append(point)

    def calculateAllPossibleBids(self):
        self.allPossibleBids = self.party.preference.bids.copy()

    def vectorizeBid(self, bid: nenv.Bid):
        point = [0. for _ in range(self.vectorSize)]

        issueIndex = 0

        for issue, value in bid:
            point[issueIndex] = self.party.preference.issue_weights[issue] * self.party.preference.value_weights[issue][value]

            issueIndex += 1

        point = normalize(point)
        point = multiply(point, 10)

        return point

    def generateBid(self, concessionRate: float) -> nenv.Bid:
        maxBid = self.party.preference.bids[0].copy()

        maxBidPoint = self.vectorizeBid(maxBid)

        delta = concessionRate
        unitVector = self.getUnitVector()

        concessionDelta = multiply(unitVector, delta)

        concessionPoint = add(maxBidPoint, concessionDelta)

        bid = self.getBidCloseToConcessionPoint(concessionPoint)

        return bid

    def getBidCloseToConcessionPoint(self, concessionPoint: list) -> nenv.Bid:
        maxBid = self.party.preference.bids[0].copy()
        maxBidPoint = self.vectorizeBid(maxBid)

        distances = [getEuclideanDistance(concessionPoint, bidPoint) for bidPoint in self.bidSpace]

        minDistance = distances[0]
        minDistanceIndex = 0

        for i in range(len(distances)):
            d = distances[i]

            if not equals(self.bidSpace[i], maxBidPoint, 0.1) and d < minDistance:
                minDistanceIndex = i
                minDistance = d

        bid = self.allPossibleBids[minDistanceIndex]

        return bid
