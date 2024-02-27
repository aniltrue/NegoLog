from typing import List


class IssueValueUnit:
    """
        This class is used in Similarity Map
    """
    valueOfIssue: str               # Name of value
    importanceList = List[float]    # List of value importances

    def __init__(self, value: str):
        """
            Constructor
        :param value: Value name
        """
        self.valueOfIssue = value
        self.importanceList = []
