from typing import List, Dict
from agents.AgentGG.ImpUnit import ImpUnit
import nenv


class ImpMap:
    """
        Importance Map is an Opponent Model which is a Frequency-Based approach. This opponent model can be used to
        estimate not only the opponents preferences but also self preferences (Uncertainty Challenge).

        It tries to predict importance of a value.
    """
    map: Dict[nenv.Issue, List[ImpUnit]]        # Importance dictionary
    pref: nenv.Preference                       # Self preferences

    def __init__(self, preference: nenv.Preference):
        """
            Constructor
        :param preference: Self preferences
        """
        self.pref = preference
        self.map = {}

        # Initiate importance units
        for issue in self.pref.issues:
            values = issue.values

            issueImpUnit = [ImpUnit(value) for value in values]

            self.map[issue] = issueImpUnit

    def opponent_update(self, receivedOfferBid: nenv.Bid):
        """
            This method is called when a bid is received from the opponent to update estimated opponent preferences.
        :param receivedOfferBid: Received bid
        :return: Nothing
        """
        for issue in self.pref.issues:
            values = issue.values
            currentIssueList = self.map[issue]

            for currentUnit in currentIssueList:
                # Update value weight when it is observed
                if currentUnit.valueOfIssue == receivedOfferBid[issue]:
                    currentUnit.meanWeightSum += 1
                    break

        for issue, impUnitList in self.map.items():     # Sort values
            self.map[issue] = sorted(impUnitList, reverse=True)

    def self_update(self, bidOrdering: list):
        """
            This method is called to estimate self preferences
        :param bidOrdering: List of bids in Preferences
        :return: Nothing
        """

        # Current Weight starts from the zero and increases depending on the importance of a bid.
        # Higher importance higher Current Weight value
        current_weight = 0

        # In the Framework, bid ordering is sorted in descending order. However, Genius sorts in ascending order.
        for bid in reversed(bidOrdering):
            # Increase current weight
            current_weight += 1

            # Update the observed values
            for issue in self.pref.issues:
                currentIssueList = self.map[issue]

                # Update corresponding values
                for currentUnit in currentIssueList:
                    if currentUnit.valueOfIssue == bid[issue]:
                        currentUnit.weightSum += current_weight
                        currentUnit.count += 1
                        break

        # Normalized values
        for impUnitList in self.map.values():
            for currentUnit in impUnitList:
                if currentUnit.count == 0:
                    currentUnit.meanWeightSum = 0.
                else:
                    currentUnit.meanWeightSum = currentUnit.weightSum / currentUnit.count

        # Sort the values in descending order
        for issue, impUnitList in self.map.items():
            self.map[issue] = sorted(impUnitList, reverse=True)

        # Minimum value must be 0
        minMeanWeightSum = 1000000000
        for issue, impUnitList in self.map.items():
            tempMeanWeightSum = impUnitList[-1].meanWeightSum

            if tempMeanWeightSum < minMeanWeightSum:
                minMeanWeightSum = tempMeanWeightSum

        for impUnitList in self.map.values():
            for currentUnit in impUnitList:
                currentUnit.meanWeightSum -= minMeanWeightSum

    def getImportance(self, bid: nenv.Bid) -> float:
        """
            Calculate the estimated importance of a given bid.
        :param bid: Target bid
        :return: Estimated importance
        """
        bidImportance = 0.

        for issue in self.pref.issues:
            value = bid[issue]

            valueImportance = 0.

            for i in self.map[issue]:
                if i.valueOfIssue == value:
                    valueImportance = i.meanWeightSum
                    break

            bidImportance += valueImportance

        return bidImportance
