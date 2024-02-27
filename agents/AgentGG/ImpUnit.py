
class ImpUnit:
    """
        Importance Unit for the opponent model
    """
    valueOfIssue: str       # Value name
    weightSum: float        # Sum of weights
    count: int              # Observation counter
    meanWeightSum: float    # Mean of weight sums

    def __init__(self, value: str):
        """
            Constructor
        :param value: Value name
        """
        self.valueOfIssue = value
        self.weightSum = 0
        self.count = 0
        self.meanWeightSum = 0.

    def __ge__(self, other):
        """
            Comparison is done by comparing the meanWeightSum value
        :param other: Other ImpUnit object
        :return: self >= other
        """
        return self.meanWeightSum >= other.meanWeightSum

    def __gt__(self, other):
        """
            Comparison is done by comparing the meanWeightSum value
        :param other: Other ImpUnit object
        :return: self > other
        """
        return self.meanWeightSum > other.meanWeightSum

    def __le__(self, other):
        """
            Comparison is done by comparing the meanWeightSum value
        :param other: Other ImpUnit object
        :return: self <= other
        """
        return self.meanWeightSum <= other.meanWeightSum

    def __lt__(self, other):
        """
            Comparison is done by comparing the meanWeightSum value
        :param other: Other ImpUnit object
        :return: self < other
        """
        return self.meanWeightSum < other.meanWeightSum
