import math
from typing import List
from nenv.Preference import Preference
from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.Bid import Bid
from scipy.stats import chisquare


class WindowedFrequencyOpponentModel(AbstractOpponentModel):
    """
        **Windowed frequency-based opponent model**:
            It extends the classical frequency-based approach by introducing the window approach. Instead of comparing
            two subsequent offers, they compare the fixed number of subsequent offers (i.e., window). They test whether
            there is a statistical difference between the distribution of issue values in a current window to determine
            whether the issue weights should be updated. For updating issue weights, *alpha* and *beta* parameters
            are used to adjust the amount of update.

            The issue update approach works well if the opponent makes a concession. However, opponents can make other
            moves, such as silent and selfish moves. Therefore, it applies the issue update if there is a concession
            between the windows. Note that these windows are consecutive and disjoint windows of the negotiation
            history of the opponent. [Tunali2017]_

        .. [Tunali2017] Tunalı, O., Aydoğan, R., Sanchez-Anguix, V. (2017). Rethinking Frequency Opponent Modeling in Automated Negotiation. In: An, B., Bazzan, A., Leite, J., Villata, S., van der Torre, L. (eds) PRIMA 2017: Principles and Practice of Multi-Agent Systems. PRIMA 2017. Lecture Notes in Computer Science(), vol 10621. Springer, Cham. <https://doi.org/10.1007/978-3-319-69131-2_16>
    """

    issues: dict
    offers: List[Bid]
    alpha: float = 10.
    beta: float = 5.
    window_size: int = 48

    @property
    def name(self) -> str:
        return "Frequency Window Opponent Model"

    def __init__(self, reference: Preference):
        super().__init__(reference)
        self.offers = []

        self.issues = {
            issue: IssueEstimator(issue.values) for issue in reference.issues
        }

        for issue in self.issues.keys():
            self.issues[issue].weight = self._pref[issue]

            for value in issue.values:
                self.issues[issue].value_counter[value] = self._pref[issue, value]
                self.issues[issue].value_weights[value] = self._pref[issue, value]

    def update(self, bid: Bid, t: float):
        self.offers.append(bid)

        if t > 0.8:  # Do Not update in the last rounds.
            self.update_weights()
            return

        for issue_name, estimator in self.issues.items():
            estimator.update(bid[issue_name])

        if len(self.offers) < 2:
            self.update_weights()
            return

        if len(self.offers) % self.window_size == 0 and len(self.offers) >= 2 * self.window_size:
            current_window = self.offers[-self.window_size:]
            previous_window = self.offers[-2 * self.window_size:-self.window_size]

            self.update_issues(previous_window, current_window, t)

        self.update_weights()

    def update_issues(self, previous_window: List[Bid], current_window: List[Bid], t: float):
        """
            Update issue weights

            :param previous_window: Previous window as a list of bids
            :param current_window: Current window as a list of bids
            :param t: Current negotiation time
            :return: Nothing
        """
        not_changed = []
        concession = False

        def frequency(window: list, issue_name: str, issue_obj: IssueEstimator):
            values = []

            for value in issue_obj.value_weights.keys():
                total = 0.

                for bid in window:
                    if bid[issue_name] == value:
                        total += 1.

                values.append((1. + total) / (len(window) + len(issue_obj.value_counter)))

            return values

        for issue_name, issue_obj in self.issues.items():
            fr_current = frequency(current_window, issue_name, issue_obj)
            fr_previous = frequency(previous_window, issue_name, issue_obj)
            p_val = chisquare(fr_previous, fr_current)[1]

            if p_val > 0.05:
                not_changed.append(issue_obj)
            else:
                estimated_current = sum([fr_current[i] * w for i, w in enumerate(issue_obj.value_weights.values())])
                estimated_previous = sum([fr_previous[i] * w for i, w in enumerate(issue_obj.value_weights.values())])

                if estimated_current < estimated_previous:
                    concession = True

        if len(not_changed) != len(self.issues) and concession:
            for issue_obj in not_changed:
                issue_obj.weight += self.alpha * (1. - math.pow(t, self.beta))

        total_issue_weights = sum([issue_obj.weight for issue_obj in self.issues.values()])

        for issue_obj in self.issues.values():
            issue_obj.weight /= total_issue_weights

    def update_weights(self):
        """
            This method updates the weights

            :return: Nothing
        """
        for issue in self.issues.keys():
            self._pref[issue] = self.issues[issue].weight

            for value in issue.values:
                self._pref[issue, value] = self.issues[issue].value_weights[value]


class IssueEstimator:
    """
        This class is a helpful class for Windowed Frequency Opponent Model
    """
    weight: float           #: The estimated weight of the issue
    value_weights: dict     #: The weights of the values under the issue
    value_counter: dict     #: The number of observation of values under the issue
    gamma: float = 0.25     #: The gamma parameter for smoothing

    def __init__(self, values: list):
        self.value_weights = {value: 1. for value in values}
        self.value_counter = {value: 1. for value in values}

        self.weight = 1.

    def update(self, value: str):
        self.value_counter[value] += 1.

        max_value = max(self.value_counter.values())

        self.value_weights = {value_name: math.pow(self.value_counter[value_name], self.gamma) / math.pow(max_value, self.gamma) for value_name in self.value_counter.keys()}
