from typing import List, Dict, Set

import nenv
from agents.AhBuNeAgent.impmap.OppIssueValueUnit import OppIssueValueUnit
from agents.AhBuNeAgent.linearorder.OppSimpleLinearOrdering import OppSimpleLinearOrderding


class OppSimilarityMap:
    """
        This class estimates the importance of values and issues for the opponent.
    """
    pref: nenv.Preference                                       # Preferences
    oppIssueValueImpMap: Dict[str, List[OppIssueValueUnit]]     # Importance of values
    oppEstimatedProfile: OppSimpleLinearOrderding               # Estimated profile
    maxImpBid: nenv.Bid                                         # The highest important bid
    availableValues: Dict[str, Set[str]]                       # Available values
    issueList: List[str]                                        # List of issues

    def __init__(self, pref: nenv.Preference):
        """
            Constructor
        :param pref: Preference of the Agent
        """
        self.pref = pref
        self.issueList = []

        # Get all issues

        for issue in pref.issues:
            self.issueList.append(issue.name)

        # Initiate dictionaries

        self.renewMaps()

    def createConditionLists(self, numFirstBids: int):
        """
            This method determines the available values from the given estimated bid utility list.
        :param numFirstBids: Number of first bids
        :return: Nothing
        """
        # Initiate lists
        self.renewLists()

        # Get estimated bids
        sortedBids = self.oppEstimatedProfile.getBids()
        firstStartIndex = (len(sortedBids) - 1) - numFirstBids

        # Start index must be >= 0
        if firstStartIndex < 0:
            firstStartIndex = 0

        # Find available values
        for bidIndex in range(firstStartIndex, len(sortedBids)):
            currentBid = sortedBids[bidIndex]

            for issue in currentBid.content.keys():
                currentIssueList = self.oppIssueValueImpMap[issue]

                for currentUnit in currentIssueList:
                    if currentUnit.valueOfIssue == currentBid[issue]:
                        if currentBid[issue] not in self.availableValues[issue]:
                            self.availableValues[issue].add(currentBid[issue])
                        break

    def isCompromised(self, bid: nenv.Bid, numFirstBids: int, minUtility: float) -> bool:
        """
            Check if the given bid is compromised with the Similarity Map
        :param bid: Target bid
        :param numFirstBids: First number of bids
        :param minUtility: Minimum utility value
        :return: Whether the given bid is compromised with the Similarity Map, or not
        """
        self.createConditionLists(numFirstBids)

        issueChangeLoss = 1. / len(self.pref.issues)

        changeRest = int((1 - minUtility) / issueChangeLoss) - 1

        if changeRest > len(self.issueList):
            changeRest = len(self.issueList)

        changedIssue = 0

        for i in range(len(self.issueList)):
            issue = self.issueList[i]

            # Available values
            availableIssueValueList = set(self.availableValues[issue])

            # If not maximum important bid
            if self.maxImpBid[issue] != bid[issue]:
                # If not available
                if bid[issue] not in availableIssueValueList:
                    changedIssue += 2
                else:
                    changedIssue += 1

        # Check numbers
        if changedIssue <= changeRest:
            return False

        return True

    def update(self, estimatedProfile: OppSimpleLinearOrderding):
        """
            This method is called when a bid is received from the opponent.
        :param estimatedProfile: Estimated profile of the opponent
        :return: Nothing
        """
        # Initiate maps
        self.renewMaps()

        # Set self estimated profile
        self.oppEstimatedProfile = estimatedProfile
        sortedBids = estimatedProfile.getBids()

        # Set max. important bids for the opponent
        self.maxImpBid = estimatedProfile.getMaxBid()

        # Iterate over sorted bids to extract the Issue-Value importance dictionary
        for bidIndex in range(len(sortedBids)):
            currentBid = sortedBids[bidIndex]
            bidImportance = float(estimatedProfile.getUtility(currentBid))

            for issue in currentBid.content.keys():
                currentIssueList = self.oppIssueValueImpMap[issue]

                for currentUnit in currentIssueList:
                    if currentBid[issue] == currentUnit.valueOfIssue:
                        currentUnit.importanceList.append(bidImportance)
                        break

    def renewMaps(self):
        """
            This method initiates the corresponding dictionaries
        :return: Nothing
        """
        self.oppIssueValueImpMap = {}

        for issue in self.pref.issues:
            values = issue.values
            issueIssueValueUnit = [OppIssueValueUnit(value) for value in values]
            self.oppIssueValueImpMap[issue.name] = issueIssueValueUnit

    def renewLists(self):
        """
            This method initiates the corresponding lists
        :return: Nothing
        """
        self.availableValues = {issue.name: set() for issue in self.pref.issues}

    def mostCompromisedBids(self) -> dict:
        """
            This method finds the most compromised bids
        :return: Sorted dictionary
        """
        # Get estimated order of bids of the opponent
        orderedBids = self.oppEstimatedProfile.getBids()

        # Max. utility bid
        maxUtilBid = orderedBids[-1]

        # List
        listOfOpponentCompremised = {}

        # Find number of values which are not the highest importance.
        for i in range(len(orderedBids)):
            testBid = orderedBids[i]
            compromiseCount = 0

            for issue in self.pref.issues:
                if maxUtilBid[issue] != testBid[issue]:
                    compromiseCount += 1

            listOfOpponentCompremised[testBid] = compromiseCount

        # Sort by the number of compromised values
        sorted = self.sortByValueBid(listOfOpponentCompremised)

        return sorted

    def sortByValueBid(self, hm: dict) -> dict:
        """
            This method sorts a given dictionary based on the values
        :param hm: Given dictionary
        :return: Sorted dictionary
        """
        list = [[key, value] for key, value in hm.items()]
        list.sort(key=lambda x: x[1])

        temp = {}

        for [key, value] in list:
            temp[key] = value

        return temp
