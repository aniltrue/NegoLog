import math
from numbers import Integral
from typing import Optional
import numpy as np
from scipy.stats import spearmanr, kendalltau, pearsonr
from nenv.Bid import Bid
from nenv.Preference import Preference
from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.OpponentModel.UniformEstimatedPreference import UniformEstimatedPreference
from nenv.OpponentModel.CBOMEstimatedPreference import CBOMEstimatedPreference
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

    DEFAULT_DEADLINE_ROUND = 1000

    def __init__(self, reference: Preference, mode: str = "uniform", deadline_round: Optional[int] = None):
        """
            Constructor

            :param reference: Reference preference to get domain information. Generally, the agent's preference is given.
            :param mode: Initial weights: ``uniform`` (default) or inverse own weights (``cbom``).
            :param deadline_round: Positive round horizon; ``None`` uses the 1000-round default.
        """
        self.initialize_preference(reference, mode)
        self.set_deadline(deadline_round)

    def initialize_preference(self, reference: Preference, mode: str = "uniform"):
        """Select equal weights (uniform) or inverse own weights (cbom)."""
        initializers = {"uniform": UniformEstimatedPreference, "cbom": CBOMEstimatedPreference}
        if not isinstance(mode, str) or mode not in initializers:
            raise ValueError("Unknown preference initialization mode: %r" % (mode,))
        self._pref = initializers[mode](reference)

    def set_deadline(self, deadline_round: Optional[int] = None):
        """Configure the positive round horizon before feeding observations.

        A missing round limit, including time-only sessions, uses 1000 rounds.
        No environment variable is read. Subclasses may call this method even
        when their constructor does not invoke the base constructor.
        """
        if deadline_round is None:
            deadline_round = self.DEFAULT_DEADLINE_ROUND
        if isinstance(deadline_round, bool) or not isinstance(deadline_round, Integral) or deadline_round <= 0:
            raise ValueError("deadline_round must be a positive integer or None")
        self.deadline_round = int(deadline_round)

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
                        return_kendall_tau: bool = True, *,
                        vectorized: bool = False) -> (Optional[float], Optional[float], Optional[float]):
        """
            This method calculates the error of the estimated preferences for the performance evaluation of the opponent
            model. There metrics are used [Baarslag2013]_ [Keskin2023]_:

            - **Root Mean Squared Error (RMSE)**: The difference between real and estimated utility of all bids in that domain.

            - **Spearman**: The ranking correlation between real and estimated bid rankings in that domain.

            - **Kendall-Tau**: The ranking correlation between real and estimated bid rankings in that domain.

            Tied utilities receive tied ranks. A rank correlation is undefined
            (NaN) when either utility vector is constant or has fewer than two
            bids. Evaluating a model does not consume the negotiation RNG.

            .. [Baarslag2013] Tim Baarslag, Mark J.C. Hendrikx, Koen V. Hindriks, and Catholijn M. Jonker. Predicting the performance of opponent models in automated negotiation. In International Joint Conferences on Web Intelligence (WI) and Intelligent Agent Technologies (IAT), 2013 IEEE/WIC/ACM, volume 2, pages 59–66, 2013.
            .. [Keskin2023] Mehmet Onur Keskin, Berk Buzcu, and Reyhan Aydoğan. Conflict-based negotiation strategy for human-agent negotiation. Applied Intelligence, 53(24):29741–29757, dec 2023.

            :param org_pref: Original preferences of the opponent to compare
            :param return_rmse: Whether RMSE will be calculated, or not
            :param return_spearman: Whether Spearman will be calculated, or not
            :param return_kendall_tau: Whether Kendall-Tau will be calculated, or not
            :param vectorized: Opt in to additive batch evaluation. Custom utility
                overrides fall back to normal calls; no preference or bid cache is retained.
            :return: The metric results (i.e., RMSE, Spearman and Kendall-Tau) as a tuple
        """
        estimated_pref = self.preference
        if vectorized:
            from nenv.utils.utility_metrics import utility_pairs
            original_utilities, estimated_utilities = utility_pairs(org_pref, estimated_pref, vectorized=True)
            utilities = list(zip(original_utilities, estimated_utilities))
        else:
            utilities = [[bid.utility, estimated_pref.get_utility(bid)] for bid in org_pref.bids]

        rmse = None

        if return_rmse:
            rmse = 0.
            for utility in utilities:
                rmse += math.pow(utility[0] - utility[1], 2.)

            rmse = math.sqrt(rmse / len(utilities))

        original_utilities = [utility[0] for utility in utilities]
        estimated_utilities = [utility[1] for utility in utilities]
        ranks_defined = (len(utilities) >= 2 and
                         len(set(original_utilities)) > 1 and
                         len(set(estimated_utilities)) > 1)

        spearman = None
        if return_spearman:
            spearman = float(spearmanr(original_utilities, estimated_utilities)[0]) if ranks_defined else math.nan

        kendall = None
        if return_kendall_tau:
            kendall = float(kendalltau(original_utilities, estimated_utilities)[0]) if ranks_defined else math.nan

        return rmse, spearman, kendall

    def calculate_additional_metrics(self, org_pref: Preference, *, pearson: bool = False,
                                     mape: bool = False, zero_utility: str = "nan",
                                     vectorized: bool = False) -> dict:
        """Opt-in statistics, separate from the existing three-value API.

        Only requested keys are returned: ``Pearson`` and/or ``MAPE``.
        Pearson is NaN for fewer than two bids or a constant vector. MAPE is a
        percentage, ``100 * mean(abs(true-estimated) / abs(true))``. If any true
        utility is zero, return NaN (default) or raise ValueError when
        ``zero_utility='raise'``; observations are never silently discarded.
        An empty domain yields NaN. This method does not add logger columns.
        """
        if zero_utility not in ("nan", "raise"):
            raise ValueError("zero_utility must be 'nan' or 'raise'")
        if not pearson and not mape:
            return {}

        from nenv.utils.utility_metrics import utility_pairs
        true, estimated = utility_pairs(org_pref, self.preference, vectorized=vectorized)
        result = {}
        if pearson:
            defined = len(true) >= 2 and len(set(true)) > 1 and len(set(estimated)) > 1
            result["Pearson"] = float(pearsonr(true, estimated)[0]) if defined else math.nan
        if mape:
            if np.any(true == 0):
                if zero_utility == "raise":
                    raise ValueError("MAPE is undefined for a zero true utility")
                result["MAPE"] = math.nan
            else:
                result["MAPE"] = float(100 * np.mean(np.abs(true-estimated) / np.abs(true))) if len(true) else math.nan
        return result
