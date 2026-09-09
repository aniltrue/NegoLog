from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.Preference import Preference

class CBOMEstimatedPreference(EstimatedPreference):
    """
        CBOM (Conflict-Based Opponent Model) initialization for opponent model preferences.
        Initializes weights as the inverse of the agent's preferences (1 - agent_weight).
        This follows the assumption that the opponent has opposite preferences.
    """
    def __init__(self, reference: Preference):
        """
            Constructor
        :param reference: Reference Preference to get domain information.
        """
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
