from typing import Dict
from .Preference import Preference, Issue


class EditablePreference(Preference):
    def __init__(self, issue_weights: Dict[str, float], issues: Dict[str, Dict[str, float]],
                 reservation_value: float = 0., generate_bids: bool = True):

        super().__init__(None)

        self.profile_json_path = ""
        self._issues = []
        self._issue_weights = {}
        self._value_weights = {}
        self._bids = []

        self._reservation_value = reservation_value

        for issue_name in issue_weights.keys():
            issue = Issue(issue_name, list(issues[issue_name].keys()))

            self._issues.append(issue)
            self._issue_weights[issue] = issue_weights[issue_name]

            self._value_weights[issue] = {}

            for value_name, value_weight in issues[issue_name].items():
                self._value_weights[issue][value_name] = value_weight

        # Normalize to ensure that weights and utilities are valid
        self.normalize()

        # Generate bids
        if generate_bids:
            _ = self.bids

    def __getitem__(self, key) -> float:
        """
            You can reach Issue and Value weight as shown in below:

            - **For Issue Weight**, you can use Issue object or IssueName (as string):
                *estimated_preference[Issue]* or *estimated_preference[IssueName]*

            - **For Value Weight**: you can use Issue-Value pair where Issue is an Issue object or IssueName as string:
                *estimated_preference[Issue, Value]* or *estimated_preference[IssueName, Value]*

            :param key: Issue or Issue-Value pair or IssueName-Value pair
            :return: Weight of Issue or Value
        """
        if isinstance(key, tuple) and len(key) == 2:
            return self._value_weights[key[0]][key[1]]

        return self._issue_weights[key]

    def __setitem__(self, key, weight: float):
        """
            You can reach Issue and Value weight as shown in below:

            - **For Issue Weight**, you can use Issue object or IssueName (as string):
                *estimated_preference[Issue] = 0.5* or *estimated_preference[IssueName] = 0.5*

            - **For Value Weight**: you can use Issue-Value pair where Issue is an Issue object or IssueName as string:
                *estimated_preference[Issue, Value] = 0.5* or *estimated_preference[IssueName, Value] = 0.5*

            :param key: Issue or Issue-Value pair or IssueName-Value pair
            :return: Weight of Issue or Value
            """
        if isinstance(key, tuple) and len(key) == 2:
            self._value_weights[key[0]][key[1]] = weight
        else:
            self._issue_weights[key] = weight

    def get_issue_weight(self, issue: Issue) -> float:
        """
            Get the weight of an issue

            :param issue: Issue object or IssueName as string
            :return: Weight of corresponding Issue
        """
        return self._issue_weights[issue]

    def get_value_weight(self, issue: Issue, value: str) -> float:
        """
            Get the utility (weight) of a value under an issue

            :param issue: Issue object or IssueName as string
            :param value: Value as string
            :return: Weight of corresponding Issue-Value pair
        """
        return self._value_weights[issue][value]

    def set_issue_weight(self, issue: Issue, weight: float):
        """
            Change Issue Weight

            :param issue: Issue object or IssueName as string
            :param weight: New weight that will be assigned
            :return: Nothing
        """
        self._issue_weights[issue] = weight

    def set_value_weight(self, issue: Issue, value: str, weight: float):
        """
            Change Value weight

            :param issue: Issue object or IssueName as string
            :param value: Value as string
            :param weight: New weight that will be assigned
            :return: Nothing
        """
        self._value_weights[issue][value] = weight

    def set_reservation_value(self, value: float):
        """
            Change *reservation* value

        :param value: New reservation value
        :return: Nothing
        """

        self._reservation_value = value

    def normalize(self):
        """
            This method normalize the Issue and Value weights.

            * Value weights must be in **[0.0-1.0]** range

            * Sum of Issue weights must be **1.0**

            :return: Nothing
        """
        issue_total = sum(self._issue_weights.values())

        for issue in self.issues:
            if issue_total == 0:
                self._issue_weights[issue] = 1. / len(self.issues)
            else:
                self._issue_weights[issue] /= issue_total
