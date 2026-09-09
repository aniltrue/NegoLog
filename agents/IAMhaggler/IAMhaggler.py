import math
from typing import List, Optional, Tuple

import numpy as np
from scipy.special import erf as scipy_erf
from sklearn.gaussian_process import GaussianProcessRegressor, kernels

import nenv


class IAMhaggler(nenv.AbstractAgent):
    """
        **IAMhaggler agent by Colin R. Williams**:
            IAMhaggler Agent predicts the negotiation time and utility when the opponent makes the highest concession.
            [Williams2012]_

        ANAC 2012 Nash category winner

        .. [Williams2012] Williams, C.R., Robu, V., Gerding, E.H., Jennings, N.R. (2012). IAMhaggler: A Negotiation Agent for Complex Environments. In: Ito, T., Zhang, M., Robu, V., Fatima, S., Matsuo, T. (eds) New Trends in Agent-Based Complex Automated Negotiations. Studies in Computational Intelligence, vol 383. Springer, Berlin, Heidelberg. <https://doi.org/10.1007/978-3-642-24696-8_10>
    """
    RISK_PARAMETER: float = 1.0                     #: Default value of Risk Factor
    lastRegressionTime: float                       #: The last negotiation time when the prediction is made
    lastRegressionUtility: float                    #: The last utility value when the prediction is made
    previousTargetUtility: float                    #: Previous target utility that the agent calculated

    MAXIMUM_ASPIRATION: float = 0.9                 #: For the acceptance strategy
    acceptMultiplier: float = 1.02                  #: For the acceptance strategy
    # Preserve the attribute name used by the existing strategy and extensions.
    lastTimeSlot: int  # noqa: N815
    discounting_factor: float                 #: Discount factor

    utilitySamples: np.ndarray                      #: Column vector (m, 1)
    timeSamples: np.ndarray                         #: Row vector (1, n+1)
    utility: np.ndarray                             #: Pre-computed utility surface (m, n+1)
    means: Optional[np.ndarray]                     #: Column vector (n+1, 1)
    variances: Optional[np.ndarray]                 #: Column vector (n+1, 1)
    matrixTimeSamplesAdjust: Optional[np.ndarray]   #: Column vector (n+1, 1)

    gp: Optional[GaussianProcessRegressor]          #: Gaussian Process state
    opponentTimes: List[float]                      #: List of opponent's action times
    opponentUtilities: List[float]                  #: List of opponent's bid's utility

    maxUtilityInTimeSlot: float                     #: Time slot when max. utility received
    maxUtility: float                               #: Received max. utility
    bestReceivedBid: Optional[nenv.Bid]             #: Received best utility
    intercept: float                                #: Learned intercept parameter
    maxOfferedUtility: float                        #: Max. offered utility to opponent
    minOfferedUtility: float                        #: Min. offered utility to opponent

    def __init__(self, preference: nenv.Preference, session_time: int,
                 estimators: List[nenv.OpponentModel.AbstractOpponentModel]):
        super().__init__(preference, session_time, estimators)
        self.session_time = session_time

    @property
    def name(self) -> str:
        return "IAMhaggler"

    def initiate(self, opponent_name: Optional[str]):
        self.discounting_factor = 1.0

        m = 100
        utility_samples_array = np.array([1.0 - (i + 0.5) / (m + 1.0) for i in range(m)])
        self.utilitySamples = utility_samples_array.reshape(m, 1)

        n = 100
        time_samples_array = np.array([i / n for i in range(n + 1)])
        self.timeSamples = time_samples_array.reshape(1, n + 1)

        discounting = self.generateDiscountingFunction(self.discounting_factor)
        risk = self.generateRiskFunction(self.RISK_PARAMETER)
        self.utility = risk * discounting

        kernel = kernels.Matern(nu=1.5) + kernels.WhiteKernel()
        self.gp = GaussianProcessRegressor(kernel, alpha=1e-6, normalize_y=False)
        self._gp_X = []
        self._gp_y = []

        self.maxUtility = 0.0
        self.previousTargetUtility = 1.0
        self.lastRegressionTime = 0.0
        self.lastRegressionUtility = 1.0
        self.opponentTimes = []
        self.opponentUtilities = []
        self.maxUtilityInTimeSlot = 0.0
        self.lastTimeSlot = -1
        self.means = None
        self.variances = None
        self.bestReceivedBid = None
        self.intercept = 0.5
        self.matrixTimeSamplesAdjust = None
        self.maxOfferedUtility = float('-inf')
        self.minOfferedUtility = float('inf')

    def receive_offer(self, bid: nenv.Bid, t: float):
        self.last_received_bids.append(bid)

    def act(self, t: float) -> nenv.Action:
        if not self.can_accept():
            max_bid = self.preference.bids[0]
            self.previousTargetUtility = max_bid.utility
            return nenv.Offer(max_bid)

        opponent_bid = self.last_received_bids[-1]
        opponent_utility = self.preference.get_utility(opponent_bid)

        if opponent_utility > self.maxUtility:
            self.bestReceivedBid = opponent_bid
            self.maxUtility = opponent_utility

        target_utility = self.getTarget(opponent_utility, t)

        if target_utility <= self.maxUtility and self.previousTargetUtility > self.maxUtility:
            return nenv.Offer(self.bestReceivedBid)

        self.previousTargetUtility = target_utility

        planned_bid = self.preference.get_random_bid(
            target_utility - 0.025, target_utility + 0.025)

        if opponent_utility * self.acceptMultiplier >= self.previousTargetUtility:
            return self.accept_action

        if opponent_utility * self.acceptMultiplier >= self.MAXIMUM_ASPIRATION:
            return self.accept_action

        if opponent_utility * self.acceptMultiplier >= planned_bid.utility:
            return self.accept_action

        return nenv.Offer(planned_bid)

    def getTarget(self, opponent_utility: float, time: float) -> float:
        self.maxOfferedUtility = max(self.maxOfferedUtility, opponent_utility)
        self.minOfferedUtility = min(self.minOfferedUtility, opponent_utility)

        time_slot = int(math.floor(time * 36))

        regression_update_required = False
        if self.lastTimeSlot == -1:
            regression_update_required = True

        if time_slot != self.lastTimeSlot:
            if self.lastTimeSlot != -1:
                slot_time = (self.lastTimeSlot + 0.5) / 36.0
                self.opponentTimes.append(slot_time)

                if len(self.opponentUtilities) == 0:
                    self.intercept = max(0.5, self.maxUtilityInTimeSlot)
                    gradient = 0.9 - self.intercept
                    # Create matrixTimeSamplesAdjust ONCE
                    time_adjust = np.array([self.intercept + gradient * t
                                            for t in self.timeSamples.flatten()])
                    self.matrixTimeSamplesAdjust = time_adjust.reshape(-1, 1)

                self.opponentUtilities.append(self.maxUtilityInTimeSlot)
                regression_update_required = True

            self.lastTimeSlot = time_slot
            self.maxUtilityInTimeSlot = 0.0

        self.maxUtilityInTimeSlot = max(self.maxUtilityInTimeSlot, opponent_utility)

        # The first opponent offer can arrive after slot zero (for example,
        # when opening a short round-based session). Wait for an observed slot
        # to close before fitting a model from its completed-slot history.
        if time_slot == 0 or not self.opponentTimes:
            return 1.0 - time / 2.0

        if regression_update_required:
            gradient = 0.9 - self.intercept

            if self.lastTimeSlot == -1:
                self.means = self.matrixTimeSamplesAdjust.copy()
                self.variances = np.zeros_like(self.means)
            else:
                x = self.opponentTimes[-1]
                y = self.opponentUtilities[-1]

                y_adjusted = y - self.intercept - (gradient * x)

                self._gp_X.append([x])
                self._gp_y.append(y_adjusted)

                X_train = np.array(self._gp_X)
                y_train = np.array(self._gp_y).ravel()
                self.gp.fit(X_train, y_train)

                time_samples_col = self.timeSamples.T
                mu, sigma = self.gp.predict(time_samples_col, return_std=True)

                self.means = (mu.reshape(-1, 1) + self.matrixTimeSamplesAdjust)
                self.variances = (sigma ** 2).reshape(-1, 1)

        prob_accept, cum_accept = self.generateProbabilityAccept(
            self.means, self.variances, time)

        prob_expected_utility = prob_accept * self.utility
        cum_expected_utility = cum_accept * self.utility

        best_time, best_utility = self.getExpectedBestAgreement(
            prob_expected_utility, cum_expected_utility, time)

        target_utility = self.lastRegressionUtility + \
                         ((time - self.lastRegressionTime) *
                          (best_utility - self.lastRegressionUtility) /
                          (best_time - self.lastRegressionTime))

        self.lastRegressionUtility = target_utility
        self.lastRegressionTime = time

        return self.limitConcession(target_utility)

    def limitConcession(self, target_utility: float) -> float:
        limit = 1.0 - ((self.maxOfferedUtility - self.minOfferedUtility) + 0.1)
        if limit > target_utility:
            return limit
        return target_utility

    def generateDiscountingFunction(self, discounting_factor: float) -> np.ndarray:
        time_samples_1d = self.timeSamples.flatten()
        m = self.utilitySamples.shape[0]
        n_plus_1 = self.timeSamples.shape[1]

        discounting = np.zeros((m, n_plus_1))
        for i in range(m):
            for j in range(n_plus_1):
                discounting[i, j] = math.pow(discounting_factor, time_samples_1d[j])

        return discounting

    def generateRiskFunction(self, risk_parameter: float) -> np.ndarray:
        r_min = self._generateRiskFunction_single(risk_parameter, 0.0)
        r_max = self._generateRiskFunction_single(risk_parameter, 1.0)
        r_range = r_max - r_min

        utility_samples_1d = self.utilitySamples.flatten()
        m = self.utilitySamples.shape[0]
        n_plus_1 = self.timeSamples.shape[1]

        risk = np.zeros((m, n_plus_1))
        for i in range(m):
            if r_range == 0:
                val = utility_samples_1d[i]
            else:
                val = (self._generateRiskFunction_single(risk_parameter, utility_samples_1d[i]) - r_min) / r_range

            for j in range(n_plus_1):
                risk[i, j] = val

        return risk

    def _generateRiskFunction_single(self, risk_parameter: float, utility: float) -> float:
        return math.pow(utility, risk_parameter)

    def generateProbabilityAccept(self, mean: np.ndarray, variance: np.ndarray,
                                  time: float) -> Tuple[np.ndarray, np.ndarray]:
        i = 0
        time_samples_1d = self.timeSamples.flatten()
        for i in range(len(time_samples_1d)):
            if time_samples_1d[i] > time:
                break

        m = self.utilitySamples.shape[0]
        n_plus_1 = self.timeSamples.shape[1]

        cumulative_accept = np.zeros((m, n_plus_1))
        probability_accept = np.zeros((m, n_plus_1))

        interval = 1.0 / m

        utility_samples_1d = self.utilitySamples.flatten()
        for col in range(i, n_plus_1):
            s = math.sqrt(2 * variance[col, 0])
            mu = mean[col, 0]

            minp = 1.0 - 0.5 * (1 + self._erf(
                (utility_samples_1d[0] + interval / 2.0 - mu) / s))
            maxp = 1.0 - 0.5 * (1 + self._erf(
                (utility_samples_1d[m - 1] - interval / 2.0 - mu) / s))

            for row in range(m):
                util = utility_samples_1d[row]

                p = 1.0 - 0.5 * (1 + self._erf((util - mu) / s))

                p1 = 1.0 - 0.5 * (1 + self._erf((util - interval / 2.0 - mu) / s))
                p2 = 1.0 - 0.5 * (1 + self._erf((util + interval / 2.0 - mu) / s))

                cumulative_accept[row, col] = (p - minp) / (maxp - minp)
                probability_accept[row, col] = (p1 - p2) / (maxp - minp)

        return probability_accept, cumulative_accept

    def _erf(self, x: float) -> float:
        if x > 6:
            return 1.0
        if x < -6:
            return -1.0

        result = scipy_erf(x)

        if result > 1:
            return 1.0
        if result < -1:
            return -1.0

        return result

    def getExpectedBestAgreement(self, prob_expected_values: np.ndarray,
                                 cum_expected_values: np.ndarray,
                                 time: float) -> Tuple[float, float]:
        prob_future = self.getFutureExpectedValues(prob_expected_values, time)
        cum_future = self.getFutureExpectedValues(cum_expected_values, time)

        col_sums = np.sum(prob_future, axis=0)
        best_col = 0
        best_col_sum = 0.0

        for x in range(col_sums.shape[0]):
            if col_sums[x] >= best_col_sum:
                best_col_sum = col_sums[x]
                best_col = x

        best_row = 0
        best_row_value = 0.0

        for y in range(cum_future.shape[0]):
            expected_value = cum_future[y, best_col]
            if expected_value > best_row_value:
                best_row_value = expected_value
                best_row = y

        original_col_index = best_col + prob_expected_values.shape[1] - prob_future.shape[1]
        best_time = self.timeSamples[0, original_col_index]
        best_utility = self.utilitySamples[best_row, 0]

        return best_time, best_utility

    def getFutureExpectedValues(self, expected_values: np.ndarray, time: float) -> np.ndarray:
        i = 0
        time_samples_1d = self.timeSamples.flatten()
        for i in range(len(time_samples_1d)):
            if time_samples_1d[i] > time:
                break

        return expected_values[:, i:]
