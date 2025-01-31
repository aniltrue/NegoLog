import math
import random
from typing import Optional
from scipy.stats import spearmanr, kendalltau
from nenv.Bid import Bid
from nenv.Preference import Preference
from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from abc import ABC, abstractmethod


class AbstractOpponentModel(ABC):
    """
        Estimators (i.e., Opponent Model) predicts the opponent's preferences during a negotiation. Each Opponent Model
        should be a subclass of *AbstractOpponentModel*. They should generate *EstimatedPreference* object which is the
        predicted preferences of the opponent agent.

        This separated structure (from the agent strategy) enables to independently develop and evaluate preference estimators via *loggers*.

        **Methods**:
            To extend  *AbstractOpponentModel* class, following methods must be implemented
                - **name**: Each estimator must have a unique name for logging purposes.
                - **update**: This method is called when an offer is received from the opponent.
                - **preference**: This method returns the estimated preferences of the opponent as an *EstimatedPreference* object.

    """
    _pref: EstimatedPreference  # Estimated preference

    def __init__(self, reference: Preference):
        """
            Constructor

            :param reference: Reference preference to get domain information. Generally, the agent's preference is given.
        """
        self._pref = EstimatedPreference(reference)

    @property
    @abstractmethod
    def name(self) -> str:
        """
            Each Opponent Model must have a name for loggers.

            :return: Name of the Opponent Model
        """
        pass

    @abstractmethod
    def update(self, bid: Bid, t: float):
        """
            This method is called when a bid is received from the opponent to update the estimation.

            :param bid: Received bid
            :param t: Negotiation time
            :return: Nothing
        """
        pass

    @property
    def preference(self) -> EstimatedPreference:
        """
            This method returns the estimated preferences of the opponent.

            :return: Estimated Preferences of the opponent
        """
        return self._pref

    def calculate_error(self, org_pref: Preference,
                        return_rmse: bool = True,
                        return_spearman: bool = True,
                        return_kendall_tau: bool = True) -> (Optional[float], Optional[float], Optional[float]):
        """
            This method calculates the error of the estimated preferences for the performance evaluation of the opponent
            model. There metrics are used [Baarslag2013]_ [Keskin2023]_:

            - **Root Mean Squared Error (RMSE)**: The difference between real and estimated utility of all bids in that domain.

            - **Spearman**: The ranking correlation between real and estimated bid rankings in that domain.

            - **Kendall-Tau**: The ranking correlation between real and estimated bid rankings in that domain.

            .. [Baarslag2013] Tim Baarslag, Mark J.C. Hendrikx, Koen V. Hindriks, and Catholijn M. Jonker. Predicting the performance of opponent models in automated negotiation. In International Joint Conferences on Web Intelligence (WI) and Intelligent Agent Technologies (IAT), 2013 IEEE/WIC/ACM, volume 2, pages 59–66, 2013.
            .. [Keskin2023] Mehmet Onur Keskin, Berk Buzcu, and Reyhan Aydoğan. Conflict-based negotiation strategy for human-agent negotiation. Applied Intelligence, 53(24):29741–29757, dec 2023.

            :param org_pref: Original preferences of the opponent to compare
            :param return_rmse: Whether RMSE will be calculated, or not
            :param return_spearman: Whether Spearman will be calculated, or not
            :param return_kendall_tau: Whether Kendall-Tau will be calculated, or not
            :return: The metric results (i.e., RMSE, Spearman and Kendall-Tau) as a tuple
        """
        estimated_pref = self.preference

        bids = org_pref.bids

        utilities = [[bid.utility, estimated_pref.get_utility(bid)] for bid in bids]

        rmse = None

        if return_rmse:
            rmse = 0.
            for utility in utilities:
                rmse += math.pow(utility[0] - utility[1], 2.)

            rmse = math.sqrt(rmse / len(utilities))

        org_indices = list(range(len(bids)))
        agent_indices = list(range(len(bids)))

        random.shuffle(agent_indices)

        agent_indices = sorted(agent_indices, key=lambda i: utilities[i][1], reverse=True)

        spearman, _ = spearmanr(org_indices, agent_indices) if return_spearman else [None, 0.]
        kendall, _ = kendalltau(org_indices, agent_indices) if return_kendall_tau else [None, 0.]

        return rmse, spearman, kendall
