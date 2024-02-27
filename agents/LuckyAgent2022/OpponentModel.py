from typing import List, Dict
from collections import defaultdict
import nenv
from nenv import Bid, Preference


class IssueEstimator:
    def __init__(self, value_set: List[str]):
        self.bids_received = 0
        self.max_value_count = 0
        self.num_values = len(value_set)
        self.value_trackers = defaultdict(ValueEstimator)
        self.weight = 0

    def update(self, value: str):
        self.bids_received += 1

        # get the value tracker of the value that is offered
        value_tracker = self.value_trackers[value]

        # register that this value was offered
        value_tracker.update()

        # update the count of the most common offered value
        self.max_value_count = max([value_tracker.count, self.max_value_count])

        # update predicted issue weight
        # the intuition here is that if the values of the receiverd offers spread out over all
        # possible values, then this issue is likely not important to the opponent (weight == 0.0).
        # If all received offers proposed the same value for this issue,
        # then the predicted issue weight == 1.0
        equal_shares = self.bids_received / self.num_values
        self.weight = (self.max_value_count - equal_shares) / (
                self.bids_received - equal_shares
        )

        # recalculate all value utilities
        for value_tracker in self.value_trackers.values():
            value_tracker.recalculate_utility(self.max_value_count, self.weight)

    def get_value_utility(self, value: str):
        if value in self.value_trackers:
            return self.value_trackers[value].utility

        return 0


class ValueEstimator:
    def __init__(self):
        self.count = 0
        self.utility = 0

    def update(self):
        self.count += 1

    def recalculate_utility(self, max_value_count: int, weight: float):
        if weight < 1:
            mod_value_count = ((self.count + 1) ** (1 - weight)) - 1
            mod_max_value_count = ((max_value_count + 1) ** (1 - weight)) - 1

            self.utility = mod_value_count / mod_max_value_count
        else:
            self.utility = 1


class OpponentModel(nenv.OpponentModel.AbstractOpponentModel):
    issue_estimators: Dict[str, IssueEstimator]

    def __init__(self, reference: Preference):
        super().__init__(reference)

        self.issue_estimators = {
            issue: IssueEstimator(issue.values) for issue in reference.issues
        }

    @property
    def name(self) -> str:
        return "LuckAgent Opponent Model"

    def update(self, bid: Bid, t: float):
        for issue, issue_estimator in self.issue_estimators.items():
            issue_estimator.update(bid[issue])

        for issue, issue_estimator in self.issue_estimators.items():
            self.preference[issue] = issue_estimator.weight

            for value in issue_estimator.value_trackers:
                self.preference[issue, value] = issue_estimator.value_trackers[value].utility

        self.preference.normalize()
