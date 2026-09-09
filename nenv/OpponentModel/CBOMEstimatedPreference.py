from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.Preference import Preference

# Keep the first-line summary (D212), rather than the conflicting D213 convention.
class CBOMEstimatedPreference(EstimatedPreference):  # noqa: D213
    """Initialize opponent weights as the inverse of the agent's preferences.

    Weights start at ``1 - agent_weight`` and are normalized. This follows the
    conflict-based model's assumption of opposite preferences.
    """

    def __init__(self, reference: Preference):
        """Initialize inverse weights from the reference domain and preferences."""
        super().__init__(reference)

    def initialize_weights(self, reference: Preference):
        """
            Initialize weights as inverse of agent's preferences.

        :param reference: Reference Preference to get domain information (agent's preference).
        """
        for issue in self._issue_weights.keys():
            self._issue_weights[issue] = 1. - reference.issue_weights[issue]

            for value in issue.values:
                self._value_weights[issue][value] = 1. - reference.value_weights[issue][value]

        self.normalize()
