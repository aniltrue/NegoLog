from typing import Dict, Union
from nenv.Issue import Issue


class IssueIterator:
    """
        This class helps to iterate Issue-Value pairs over a given bid. You can iterate over Bid object as shown below:

        :Example:
            Example of iterating issue-value pairs
            >>> for issue, value in bid:
            >>>     ...
    """
    def __init__(self, content: dict):
        self.content = content
        self.index = 0

    def __next__(self):
        if self.index < len(self.content):
            self.index += 1

            return list(self.content.keys())[self.index - 1], self.content[list(self.content.keys())[self.index - 1]]

        raise StopIteration


class Bid:
    """
        Bid class can hold the offer content and corresponding utility value.
    """
    content: Dict[Issue, str]  #: Corresponding offer content as dictionary.
    utility: float             #: Utility value of the bid. It may be unassigned (-1).

    def __init__(self, content: dict, utility: float = -1):
        """
            Constructor

            :param content: Offer content as a dictionary
            :param utility: Utility value of the bid. Default value = -1, means that the utility value was not assigned.
        """
        self.content = content
        self.utility = utility

    def __eq__(self, other: Union[int, float, Dict[Issue, str], object]):
        """
            '==' operator implementation for the Bid class. A bid object can be compared with:

            - Another Bid object or offer content: Checks if the offer content of this bid and given offer content are equal.

            - Utility value: Checks if the utility value of this bid and given utility value are equal.


            :param other: Another bid object, or offer content or utility value
            :return: Comparison result as boolean
        """
        if isinstance(other, int) or isinstance(other, float):
            return other == self.utility

        if (not isinstance(other, Bid)) and (not isinstance(other, dict)):
            return False

        for issue in self.content.keys():
            if other[issue] != self.content[issue]:
                return False

        return True

    def __iter__(self):
        """
            You can iterate Issue-Value pairs over the Bid object as shown below:

            :Example:
                Example of iterating issue-value pairs
                >>> for issue, value in bid:
                >>>     ...

            :return: IssueIterator that will be called in for-loop.
        """
        return IssueIterator(self.content)

    def __getitem__(self, issue):
        """
            You can get the corresponding value of the given issue.

            :Example:
                Examples of getting value of an issue
                >>> value = bid[issue]
                >>> value = bid[issueName]

            :param issue: Issue object or issue name as string
            :return: Corresponding value
        """
        return self.content[issue]

    def __setitem__(self, key, value):
        """
            You can set a value to an issue.

            :Example:
                Examples of setting value to an issue
                >>> bid[issue] = value
                >>> bid[issueName] = value


            :param key: Issue object or issue name as string

            :param value: New value that will be assigned
            :return: Nothing
        """
        self.content[key] = value

    def __hash__(self):
        """
            The hash value of the bid is created based on the offer content.

            :return: Hash value of the bid
        """
        return self.content.__str__().__hash__()

    def __str__(self):
        """
            The string version of the bid is created based on the offer content.

            :return: Offer content as string
        """
        return self.content.__str__()

    def __repr__(self):
        """
            The representation of the bid is created based on the offer content.

            :return: Offer content
        """
        return self.content.__repr__()

    def __ge__(self, other):
        """
            '>=' operator implementation for the Bid class. A bid object can be compared with another Bid or utility
            value. This method compares the utility value of the bid and given bid's utility value.

            :param other: Another bid object or utility value
            :return: bid >= other
        """
        if isinstance(other, Bid):
            return self.utility >= other.utility

        return self.utility >= other

    def __gt__(self, other):
        """
            '>' operator implementation for the Bid class. A bid object can be compared with another Bid or utility
            value. This method compares the utility value of the bid and given bid's utility value.

            :param other: Another bid object or utility value
            :return: bid > other
        """
        if isinstance(other, Bid):
            return self.utility > other.utility

        return self.utility > other

    def __le__(self, other):
        """
            '<=' operator implementation for the Bid class. A bid object can be compared with another Bid or utility
            value. This method compares the utility value of the bid and given bid's utility value.

            :param other: Another bid object or utility value
            :return: bid <= other
        """
        if isinstance(other, Bid):
            return self.utility <= other.utility

        return self.utility <= other

    def __lt__(self, other):
        """
            '<' operator implementation for the Bid class. A bid object can be compared with another Bid or utility
            value. This method compares the utility value of the bid and given bid's utility value.

            :param other: Another bid object or utility value
            :return: bid < other
        """
        if isinstance(other, Bid):
            return self.utility < other.utility

        return self.utility < other

    def __copy__(self):
        """

            :return: Copy of the Bid object with utility value.
        """
        return Bid(self.content.copy(), self.utility)

    def copy(self):
        """

            :return: Copy of the Bid object with utility value.
        """
        return self.__copy__()

    def copy_without_utility(self):
        """

            :return: Copy of the Bid object without utility value.
        """
        bid = self.__copy__()

        bid.utility = -1.

        return bid
