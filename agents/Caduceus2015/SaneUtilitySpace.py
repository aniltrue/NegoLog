import nenv.OpponentModel


class SaneUtilitySpace(nenv.OpponentModel.EstimatedPreference):
    def __init__(self, reference: nenv.Preference):
        super().__init__(reference)

    def init_zero(self):
        for issue in self.issue_weights.keys():
            self._issue_weights[issue] = 0.

            for value_name in self.value_weights[issue].keys():
                self._value_weights[issue][value_name] = 0.

    def init_copy(self, pref: nenv.Preference):
        for issue in self.issue_weights.keys():
            self._issue_weights[issue] = pref.issue_weights[issue]

            for value_name in self.value_weights[issue].keys():
                self._value_weights[issue][value_name] = pref.value_weights[issue][value_name]

    def normalize(self):
        issueSum = sum(self.issue_weights.values())

        for issue in self.issue_weights.keys():
            self._issue_weights[issue] /= issueSum

            valueSum = sum(self.value_weights[issue].values())

            for value in self.value_weights[issue].keys():
                self._value_weights[issue][value] /= valueSum
