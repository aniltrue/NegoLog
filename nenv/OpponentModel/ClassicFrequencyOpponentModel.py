from typing import List, Dict
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.Preference import Preference
from nenv.Bid import Bid, Issue


class ClassicFrequencyOpponentModel(AbstractOpponentModel):
    """
        **Classical Frequency-based opponent model**:
            In the classical frequency-based approaches, agents have two heuristics:
             - The opponent concedes less on important issues

             - The preferred values appear more often in the opponent's offers (i.e., a negotiator tends to offer the most desired values).

            If a given value for an issue appears more frequently, the evaluation value of that value increases.
            [Krimpen2013]_

        .. [Krimpen2013] van Krimpen, T., Looije, D., Hajizadeh, S. (2013). HardHeaded. In: Ito, T., Zhang, M., Robu, V., Matsuo, T. (eds) Complex Automated Negotiations: Theories, Models, and Software Competitions. Studies in Computational Intelligence, vol 435. Springer, Berlin, Heidelberg. <https://doi.org/10.1007/978-3-642-30737-9_17>
    """

    issue_counts: Dict[Issue, float]                #: The number of changes for each issue
    value_counts: Dict[Issue, Dict[str, float]]     #: The number of observation for each value under each issue
    alpha: float                                    #: Alpha parameter for issue weight update
    opponent_bids: List[Bid]                        #: The list of received bids

    def __init__(self, reference: Preference):
        super().__init__(reference)

        self.alpha = 0.1
        self.opponent_bids = []
        self.issue_counts = {}
        self.value_counts = {}

        for issue in reference.issues:
            self.issue_counts[issue] = self._pref[issue]

            self.value_counts[issue] = {}

            for value in issue.values:
                self.value_counts[issue][value] = self._pref[issue, value]

        self._pref.normalize()

    @property
    def name(self) -> str:
        return "Classic Frequency Opponent Model"

    def update(self, bid: Bid, t: float):
        self.opponent_bids.append(bid)

        for issue, value in bid:
            self.value_counts[issue][value] += 1.

            if len(self.opponent_bids) >= 2 and self.opponent_bids[-2][issue] == value:
                self.issue_counts[issue] += self.alpha * (1. - t)

        self.update_weights()

    def update_weights(self):
        """
            This method updates the weights

            :return: Nothing
        """
        sum_issues = sum(self.issue_counts.values())

        for issue in self._pref.issues:
            self._pref[issue] = self.issue_counts[issue] / sum_issues

            max_value = max(self.value_counts[issue].values())

            for value in issue.values:
                self._pref[issue, value] = self.value_counts[issue][value] / max_value
