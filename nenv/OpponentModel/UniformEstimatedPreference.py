from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.Preference import Preference

# Keep the first-line summary (D212), rather than the conflicting D213 convention.
class UniformEstimatedPreference(EstimatedPreference):  # noqa: D213
    """Initialize opponent preferences with equal issue and value weights.

    Issue weights are ``1 / number_of_issues``. Value weights are equal within
    each issue; max-normalization makes every value weight 1.
    """

    def __init__(self, reference: Preference):
        """Initialize uniform weights over the reference domain."""
        super().__init__(reference)

    def initialize_weights(self, reference: Preference):  # noqa: D213
        """Initialize all weights uniformly.

        :param reference: Reference Preference to get domain information.
        """
        num_issues = len(self._issue_weights)

        for issue in self._issue_weights.keys():
            self._issue_weights[issue] = 1.0 / num_issues

            num_values = len(issue.values)

            for value in issue.values:
                self._value_weights[issue][value] = 1.0 / num_values

        self.normalize()
